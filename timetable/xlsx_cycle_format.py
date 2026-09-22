"""Формат XLSX для цикла: имена листов, поля, шапки, ширины колонок.

Общий модуль для импорта, экспорта и генерации шаблона.
Никакой логики парсинга или записи данных — только структура.
"""

SHEET_CYCLE = "Цикл"
SHEET_LESSONS = "Занятия"


# (latin, russian_title) — порядок фиксирован и используется всеми потребителями.
CYCLE_FIELDS = (
    ("compiled_by", "Составил"),
    ("funding", "Финансирование"),
    ("base", "База"),
    ("name", "Название цикла"),
    ("start_date", "Дата начала"),
    ("end_date", "Дата окончания"),
)

LESSON_FIELDS = (
    ("date", "Дата"),
    ("time_start", "Начало"),
    ("hours", "Часы"),
    ("lesson_type_code", "Код типа занятия"),
    ("topic", "Тема"),
    ("employee", "Преподаватель"),
    ("break_after_minutes", "Перемена после, мин"),
    ("base", "База занятия"),
)


# Производные словари для парсера.
CYCLE_LATIN = {latin for latin, _ in CYCLE_FIELDS}
CYCLE_RU_TO_LATIN = {ru: latin for latin, ru in CYCLE_FIELDS}
LESSON_LATIN_TO_INDEX = {latin: i for i, (latin, _) in enumerate(LESSON_FIELDS)}
LESSON_RU_TO_LATIN = {ru: latin for latin, ru in LESSON_FIELDS}


def write_cycle_sheet_header(ws, values: dict | None = None) -> None:
    values = values or {}
    ws.append(["Русское", "Латиница", "Значение"])
    for latin, ru in CYCLE_FIELDS:
        ws.append([ru, latin, values.get(latin, "")])


def write_lessons_sheet_header(ws) -> None:
    """Шапка листа «Занятия»: две строки — русская и латинская."""
    ws.append([ru for _, ru in LESSON_FIELDS])
    ws.append([latin for latin, _ in LESSON_FIELDS])


def set_cycle_sheet_widths(ws) -> None:
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 40


def set_lessons_sheet_widths(ws) -> None:
    for i in range(1, len(LESSON_FIELDS) + 1):
        ws.column_dimensions[chr(64 + i)].width = 20