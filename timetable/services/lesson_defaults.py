"""Заполнение group и category занятия по коду типа занятия."""
from typing import Iterable


GROUP_BY_CODE: dict[str, str] = {
    "0":  "",
    "1":  "1",
    "2":  "2",
    "3":  "3",
    "4":  "4",
    "5":  "5",
    "6":  "6",
    "7":  "1",
    "8":  "2",
    "9":  "",
    "10": "3",
}

CATEGORY_BY_CODE: dict[str, str] = {
    "0":  "lecture",
    "1":  "practice",
    "2":  "practice",
    "3":  "practice",
    "4":  "practice",
    "5":  "practice",
    "6":  "practice",
    "7":  "seminar",
    "8":  "seminar",
    "9":  "attestation",
    "10": "seminar",
}


def fill_empty_defaults(lessons: Iterable) -> list:
    """
    Заполняет пустые group и category по коду типа занятия.

    Мутирует переданные объекты в памяти. Возвращает список тех,
    у которых изменилось хотя бы одно поле.

    Если у занятия уже что-то заполнено — не трогает. Если код типа
    занятия неизвестен — пропускает.
    """
    changed = []

    for lesson in lessons:
        code = lesson.lesson_type.code
        touched = False

        if not lesson.group:
            new_group = GROUP_BY_CODE.get(code, "")
            if new_group:
                lesson.group = new_group
                touched = True

        if not lesson.category:
            new_category = CATEGORY_BY_CODE.get(code, "")
            if new_category:
                lesson.category = new_category
                touched = True

        if touched:
            changed.append(lesson)

    return changed