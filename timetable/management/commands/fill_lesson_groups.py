"""
Разовая команда: заполняет Lesson.group и Lesson.category по коду типа занятия.

После применения команду можно удалить — это утилита, а не часть
приложения.

Правила:

* код 0 (лекция)         → group="",  category="lecture"
* код 1–6 (практика N)   → group="N", category="practice"
* код 7 (семинар 1)      → group="1", category="seminar"
* код 8 (семинар 2)      → group="2", category="seminar"
* код 10 (семинар 3)     → group="3", category="seminar"
* код 9 (аттестация)     → group="",  category="attestation"

Уже заполненные поля не трогаются: если group уже проставлен, а
category пуст — заполнится только category.

Аргументов не принимает.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from timetable.models import Lesson


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


class Command(BaseCommand):
    help = (
        "Разово заполняет группы и категории занятий по коду типа занятия."
    )

    def handle(self, *args, **options):
        qs = (
            Lesson.objects
            .filter(Q(group="") | Q(category=""))
            .select_related("lesson_type")
        )

        to_update: list[Lesson] = []
        unknown_codes: set[str] = set()

        for lesson in qs:
            code = lesson.lesson_type.code

            if code not in GROUP_BY_CODE:
                unknown_codes.add(code)
                continue

            changed = False

            if not lesson.group:
                new_group = GROUP_BY_CODE[code]
                if new_group:
                    lesson.group = new_group
                    changed = True

            if not lesson.category:
                new_category = CATEGORY_BY_CODE.get(code, "")
                if new_category:
                    lesson.category = new_category
                    changed = True

            if changed:
                to_update.append(lesson)

        if to_update:
            Lesson.objects.bulk_update(to_update, ["group", "category"])

        self.stdout.write(self.style.SUCCESS(
            f"Обновлено занятий: {len(to_update)}."
        ))
        if unknown_codes:
            self.stdout.write(self.style.WARNING(
                "Неизвестные коды типов, занятия с ними не тронуты: "
                + ", ".join(sorted(unknown_codes))
            ))