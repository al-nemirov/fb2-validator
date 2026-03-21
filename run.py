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

import argparse
import glob
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.validator import validate_fb2, compile_xsd, load_xsd, format_results


def setup_logging(verbose: bool = False) -> None:
    """Настройка логирования."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


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


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="fb2-validator",
        description="Валидация файлов формата FictionBook 2.0/2.1. "
                    "Проверяет: well-formed XML, XSD-схему, структуру документа.",
        epilog="Примеры:\n"
               "  python run.py book.fb2\n"
               "  python run.py *.fb2\n"
               "  python run.py /path/to/books/\n"
               "  python run.py book.fb2 --report\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=["."],
        help="FB2-файлы или директории для валидации (по умолчанию: текущая директория)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="сохранить отчёт в файл (fb2_report_YYYYMMDD_HHMMSS.txt)",
    )
    parser.add_argument(
        "--no-xsd",
        action="store_true",
        help="пропустить XSD-валидацию",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="подробный вывод (DEBUG)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    files = collect_files(args.files)

    if not files:
        logger.error("FB2-файлы не найдены")
        sys.exit(1)

    logger.info(f"Найдено файлов: {len(files)}")

    # Загрузка и компиляция XSD (один раз для всех файлов)
    xsd_schema = None
    if not args.no_xsd:
        xsd_content = load_xsd()
        if xsd_content:
            xsd_schema = compile_xsd(xsd_content)

    # Валидация
    results = []
    for i, fp in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] {fp.name}")
        result = validate_fb2(str(fp), xsd_schema=xsd_schema)
        results.append(result)

    # Вывод
    output = format_results(results)
    print(f"\n{output}")

    # Сохранение отчёта с меткой времени
    if args.report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"fb2_report_{timestamp}.txt"
        Path(report_path).write_text(output, encoding="utf-8")
        logger.info(f"Отчёт сохранён: {report_path}")


if __name__ == "__main__":
    main()
