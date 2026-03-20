# FB2 Validator

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![lxml](https://img.shields.io/badge/lxml-4.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

Валидатор файлов формата FictionBook 2.0/2.1. Проверяет корректность XML, соответствие XSD-схеме и структуру документа.

## Возможности

- Валидация well-formed XML
- XSD-валидация по официальной схеме FictionBook 2.1
- Проверка структуры: `title-info`, `document-info`, `body`, `coverpage`
- Проверка порядка элементов в `<description>`
- Поддержка FictionBook 2.0 и 2.1
- Пакетная обработка (директория / glob-паттерн)
- Автозагрузка и кеширование XSD-схемы
- Экспорт отчёта в файл

## Структура

```
fb2-validator/
├── run.py              # Точка входа (CLI)
├── requirements.txt
├── src/
│   ├── __init__.py
│   └── validator.py    # Ядро валидатора
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Установка

```bash
git clone https://github.com/al-nemirov/fb2-validator.git
cd fb2-validator
pip install -r requirements.txt
```

## Использование

```bash
# Один файл
python run.py book.fb2

# Все FB2 в директории
python run.py /path/to/books/

# С отчётом
python run.py *.fb2 --report

# Без XSD (только структура)
python run.py book.fb2 --no-xsd
```

### Опции

| Опция | Описание |
|-------|----------|
| `--report` | Сохранить отчёт в `fb2_report.txt` |
| `--no-xsd` | Пропустить XSD-валидацию |
| `-v`, `--verbose` | Подробный вывод |
| `-h`, `--help` | Справка |

### Пример вывода

```
Результаты валидации FB2
============================================================

  Файл: book.fb2 [VALID]
  ✓ Well-formed XML
  Формат: FictionBook 2.0
  ✓ XSD Valid

  Структура:
    title-info:    ✓
    document-info: ✓
    body:          ✓
    coverpage:     ✓
    порядок:       ✓
    binary:        12
------------------------------------------------------------

Итого: 1 файлов | Валидных: 1 | Проблемных: 0
```

## Проверки

| Проверка | Описание |
|----------|----------|
| Well-formed XML | Корректность XML-разметки |
| XSD | Соответствие схеме FictionBook 2.1 |
| title-info | Наличие метаданных книги |
| document-info | Информация о документе |
| body | Тело книги |
| coverpage | Обложка |
| Порядок элементов | Правильный порядок в `<description>` |
| Binary | Количество встроенных изображений |

## Лицензия

[MIT](LICENSE)
