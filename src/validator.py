"""
Ядро валидатора FB2.
====================
Well-formed XML → XSD-валидация → проверка структуры FictionBook.
"""

import hashlib
import logging
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

from lxml import etree

logger = logging.getLogger(__name__)

# Поддерживаемые пространства имён FictionBook
FB2_NAMESPACES = {
    "2.0": "http://www.gribuser.ru/xml/fictionbook/2.0",
    "2.1": "http://www.gribuser.ru/xml/fictionbook/2.1",
}

# XSD-схемы для валидации
XSD_URLS = {
    "2.1": "https://raw.githubusercontent.com/ru-files/fictionbook2.1-schema/master/fictionbook2.1.xsd",
}

# Pinned SHA256 hash for XSD integrity check
XSD_SHA256 = "ed67ad87d5c45dbe73369c0da6d2e8850dbf3ee2c1bdd6f799bf746a5bb4ca14"

# Bundled fallback XSD (shipped with the package)
_FALLBACK_XSD = Path(__file__).parent / "fb2_2_1_fallback.xsd"

# Known FB2 format versions
KNOWN_FB2_VERSIONS = {"2.0", "2.1"}

# Ожидаемый порядок элементов в <description>
DESCRIPTION_ORDER = [
    "title-info",
    "src-title-info",
    "document-info",
    "publish-info",
    "custom-info",
]


def compile_xsd(xsd_content: bytes) -> Optional[etree.XMLSchema]:
    """
    Скомпилировать XSD-схему один раз для повторного использования.

    Args:
        xsd_content: содержимое XSD-схемы (bytes).

    Returns:
        Скомпилированная XMLSchema или None при ошибке.
    """
    try:
        return etree.XMLSchema(etree.XML(xsd_content))
    except etree.XMLSchemaError as e:
        logger.error(f"Ошибка компиляции XSD: {e}")
        return None


def validate_fb2(file_path: str,
                 xsd_content: Optional[bytes] = None,
                 xsd_schema: Optional[etree.XMLSchema] = None) -> Dict[str, Any]:
    """
    Валидация FB2-файла.

    Выполняет три уровня проверки:
    1. Well-formed XML
    2. XSD-валидация (если доступна схема)
    3. Проверка структуры FictionBook

    Args:
        file_path: путь к FB2-файлу.
        xsd_content: содержимое XSD-схемы (bytes), None = без XSD.
            Устарело: используйте xsd_schema.
        xsd_schema: скомпилированная XMLSchema (предпочтительно).

    Returns:
        Словарь с результатами валидации.
    """
    path = Path(file_path)
    results: Dict[str, Any] = {
        "file": path.name,
        "path": str(path),
        "well_formed": False,
        "xsd_valid": False,
        "errors": [],
        "warnings": [],
        "structure": {
            "namespace": None,
            "fb_version": None,
            "title_info": False,
            "document_info": False,
            "body_exists": False,
            "binary_count": 0,
            "cover_exists": False,
            "sequence_valid": False,
        },
    }

    if not path.exists():
        results["errors"].append(f"Файл не найден: {file_path}")
        return results

    # === Шаг 1: Well-formed XML ===
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        results["well_formed"] = True
    except ET.ParseError as e:
        results["errors"].append(f"XML: {e}")
        return results

    # Определение пространства имён и версии
    namespace = root.tag.split("}")[0][1:] if "}" in root.tag else None
    results["structure"]["namespace"] = namespace

    fb_version = None
    for ver, ns in FB2_NAMESPACES.items():
        if namespace == ns:
            fb_version = ver
            break
    results["structure"]["fb_version"] = fb_version

    if fb_version is None and namespace:
        results["warnings"].append(
            f"Неизвестное пространство имён: {namespace}"
        )

    # Версия из атрибута (только известные)
    xml_version = root.attrib.get("version", "")
    if xml_version:
        if xml_version in KNOWN_FB2_VERSIONS:
            results["structure"]["fb_version"] = xml_version
        else:
            results["warnings"].append(
                f"Неизвестная версия в атрибуте: {xml_version}"
            )

    # === Шаг 2: XSD-валидация ===
    schema = xsd_schema
    if schema is None and xsd_content:
        schema = compile_xsd(xsd_content)
    if schema is not None:
        try:
            parser = etree.XMLParser(schema=schema)
            etree.parse(str(path), parser)
            results["xsd_valid"] = True
        except etree.XMLSchemaError as e:
            results["errors"].append(f"XSD: {e}")
        except etree.XMLSyntaxError as e:
            results["errors"].append(f"XSD Syntax: {e}")
        except Exception as e:
            results["errors"].append(f"Валидация: {e}")

    # === Шаг 3: Проверка структуры ===
    try:
        ns_prefix = namespace or ""
        ns = {"fb": ns_prefix} if ns_prefix else {}

        def find(xpath: str):
            return root.find(xpath, namespaces=ns) if ns else root.find(xpath)

        def findall(xpath: str):
            return root.findall(xpath, namespaces=ns) if ns else root.findall(xpath)

        results["structure"]["title_info"] = find("fb:description/fb:title-info") is not None
        results["structure"]["document_info"] = find("fb:description/fb:document-info") is not None
        results["structure"]["body_exists"] = find("fb:body") is not None
        results["structure"]["cover_exists"] = find("fb:description/fb:title-info/fb:coverpage") is not None
        results["structure"]["binary_count"] = len(findall("fb:binary"))

        # Порядок элементов в <description>
        description = find("fb:description")
        if description is not None:
            actual_tags = [child.tag.split("}")[-1] for child in description]
            filtered = [t for t in actual_tags if t in DESCRIPTION_ORDER]
            results["structure"]["sequence_valid"] = filtered == sorted(
                filtered, key=lambda x: DESCRIPTION_ORDER.index(x)
            )

        # Предупреждения о пропущенных обязательных элементах
        if not results["structure"]["title_info"]:
            results["warnings"].append("Отсутствует <title-info>")
        if not results["structure"]["document_info"]:
            results["warnings"].append("Отсутствует <document-info>")
        if not results["structure"]["body_exists"]:
            results["warnings"].append("Отсутствует <body>")

    except Exception as e:
        results["errors"].append(f"Структура: {e}")
        logger.debug(traceback.format_exc())

    return results


def _verify_xsd(content: bytes) -> bool:
    """Проверить целостность XSD по SHA256-хешу."""
    digest = hashlib.sha256(content).hexdigest()
    if digest != XSD_SHA256:
        logger.warning(f"XSD: хеш не совпадает (ожидался {XSD_SHA256[:16]}…, "
                       f"получен {digest[:16]}…)")
        return False
    return True


def load_xsd(local_path: str = "fictionbook2.1.xsd") -> Optional[bytes]:
    """
    Загрузить XSD-схему: сначала локально, затем из сети,
    с проверкой SHA256-хеша.  В крайнем случае — встроенная копия.

    Args:
        local_path: путь к локальной копии XSD.

    Returns:
        Содержимое схемы (bytes) или None.
    """
    # Локальная копия
    if Path(local_path).exists():
        try:
            content = Path(local_path).read_bytes()
            if _verify_xsd(content):
                logger.info(f"XSD-схема: {local_path}")
                return content
            logger.warning(f"XSD: локальная копия повреждена, пропускаем")
        except Exception as e:
            logger.warning(f"Ошибка чтения схемы: {e}")

    # Скачивание
    url = XSD_URLS.get("2.1")
    if url:
        logger.info("Загрузка XSD-схемы...")
        try:
            with urlopen(url, timeout=15) as response:
                content = response.read()

            if _verify_xsd(content):
                # Кешируем локально
                try:
                    Path(local_path).write_bytes(content)
                    logger.info(f"Схема сохранена: {local_path}")
                except Exception:
                    pass
                return content
            logger.warning("XSD: загруженная схема не прошла проверку хеша")
        except Exception as e:
            logger.warning(f"Ошибка загрузки схемы: {e}")

    # Встроенная fallback-копия
    if _FALLBACK_XSD.exists():
        try:
            content = _FALLBACK_XSD.read_bytes()
            if _verify_xsd(content):
                logger.info("XSD-схема: встроенная fallback-копия")
                return content
            logger.warning("XSD: fallback-копия повреждена")
        except Exception as e:
            logger.warning(f"Ошибка чтения fallback-копии: {e}")

    return None


def format_results(results: List[Dict[str, Any]]) -> str:
    """Форматировать результаты в читаемый текст."""
    lines: List[str] = []
    lines.append("Результаты валидации FB2")
    lines.append("=" * 60)

    for r in results:
        is_valid = r["well_formed"] and not r["errors"]
        status = "VALID" if is_valid else "INVALID"
        lines.append(f"\n  Файл: {r['file']} [{status}]")

        if not r["well_formed"]:
            lines.append("  ✗ Некорректный XML")
            for err in r["errors"]:
                lines.append(f"    - {err}")
            continue

        lines.append("  ✓ Well-formed XML")

        s = r["structure"]
        fb_ver = s["fb_version"] or "?"
        lines.append(f"  Формат: FictionBook {fb_ver}")
        lines.append(f"  Namespace: {s['namespace']}")

        if r.get("xsd_valid"):
            lines.append("  ✓ XSD Valid")

        for err in r["errors"]:
            lines.append(f"  ✗ {err}")

        for warn in r["warnings"]:
            lines.append(f"  ⚠ {warn}")

        lines.append("")
        lines.append("  Структура:")
        lines.append(f"    title-info:    {'✓' if s['title_info'] else '✗'}")
        lines.append(f"    document-info: {'✓' if s['document_info'] else '✗'}")
        lines.append(f"    body:          {'✓' if s['body_exists'] else '✗'}")
        lines.append(f"    coverpage:     {'✓' if s['cover_exists'] else '✗'}")
        lines.append(f"    порядок:       {'✓' if s['sequence_valid'] else '✗'}")
        lines.append(f"    binary:        {s['binary_count']}")
        lines.append("-" * 60)

    # Статистика
    total = len(results)
    valid = sum(1 for r in results if r["well_formed"] and not r["errors"])
    lines.append(f"\nИтого: {total} файлов | Валидных: {valid} | Проблемных: {total - valid}")

    return "\n".join(lines)
