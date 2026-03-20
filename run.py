#!/usr/bin/env python3
"""
FB2 Validator — точка входа.
============================

Использование:
    python run.py book.fb2                  — валидация одного файла
    python run.py *.fb2                     — валидация всех FB2 в папке
    python run.py /path/to/books/           — валидация всех FB2 в директории
    python run.py book.fb2 --report         — сохранить отчёт в файл
    python run.py --help                    — справка
"""

import glob
import logging
import sys
from pathlib import Path

from src.validator import validate_fb2, load_xsd, format_results


def setup_logging(verbose: bool = False) -> None:
    """Настройка логирования."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def print_help() -> None:
    """Вывести справку."""
    print("""
FB2 Validator v1.0.0
=====================

Валидация файлов формата FictionBook 2.0/2.1.
Проверяет: well-formed XML, XSD-схему, структуру документа.

Использование:
    python run.py <файлы или директория> [опции]

Примеры:
    python run.py book.fb2
    python run.py *.fb2
    python run.py /path/to/books/
    python run.py book.fb2 --report

Опции:
    --report          Сохранить отчёт в fb2_report.txt
    --no-xsd          Пропустить XSD-валидацию
    -v, --verbose     Подробный вывод
    -h, --help        Справка
""")


def collect_files(args: list) -> list:
    """Собрать список FB2-файлов из аргументов."""
    files = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            files.extend(sorted(p.glob("*.fb2")))
            files.extend(sorted(p.glob("*.FB2")))
        elif p.is_file() and p.suffix.lower() in (".fb2",):
            files.append(p)
        else:
            # Попробовать как glob-паттерн
            matched = glob.glob(arg)
            for m in matched:
                mp = Path(m)
                if mp.is_file() and mp.suffix.lower() in (".fb2",):
                    files.append(mp)

    return list(dict.fromkeys(files))  # Убрать дубли, сохранить порядок


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        print_help()
        return

    # Парсинг аргументов
    file_args = []
    save_report = False
    skip_xsd = False
    verbose = False

    for arg in sys.argv[1:]:
        if arg == "--report":
            save_report = True
        elif arg == "--no-xsd":
            skip_xsd = True
        elif arg in ("-v", "--verbose"):
            verbose = True
        else:
            file_args.append(arg)

    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    # Если нет аргументов-файлов, ищем в текущей директории
    if not file_args:
        file_args = ["."]

    files = collect_files(file_args)

    if not files:
        logger.error("FB2-файлы не найдены")
        sys.exit(1)

    logger.info(f"Найдено файлов: {len(files)}")

    # Загрузка XSD
    xsd_content = None
    if not skip_xsd:
        xsd_content = load_xsd()

    # Валидация
    results = []
    for i, fp in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] {fp.name}")
        result = validate_fb2(str(fp), xsd_content)
        results.append(result)

    # Вывод
    output = format_results(results)
    print(f"\n{output}")

    # Сохранение отчёта
    if save_report:
        report_path = "fb2_report.txt"
        Path(report_path).write_text(output, encoding="utf-8")
        logger.info(f"Отчёт сохранён: {report_path}")


if __name__ == "__main__":
    main()
