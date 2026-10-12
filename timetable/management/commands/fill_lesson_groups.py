"""
Разовая команда: заполняет Lesson.group по коду типа занятия.

После применения команду можно удалить — это утилита, а не часть
приложения.

Правила:

* код 0 (лекция)         → группа ""
* код 9 (аттестация)     → группа ""
* код 1–6 (практика N)   → группа "N"
* код 7 (семинар 1)      → группа "1"
* код 8 (семинар 2)      → группа "2"
* код 10 (семинар 3)     → группа "3"

Уже заполненные группы не трогаются. Работает по всем занятиям.
Аргументов не принимает.
"""
from django.core.management.base import BaseCommand

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


class Command(BaseCommand):
    help = "Разово заполняет группы занятий по коду типа занятия."

    def handle(self, *args, **options):
        qs = (
            Lesson.objects
            .filter(group="")
            .select_related("lesson_type")
        )

        to_update: list[Lesson] = []
        unknown_codes: set[str] = set()

        for lesson in qs:
            code = lesson.lesson_type.code
            new_group = GROUP_BY_CODE.get(code)
            if new_group is None:
                unknown_codes.add(code)
                continue
            if not new_group:
                # тип без группы — оставляем пусто, ничего не пишем
                continue
            lesson.group = new_group
            to_update.append(lesson)

        if to_update:
            Lesson.objects.bulk_update(to_update, ["group"])

        self.stdout.write(self.style.SUCCESS(
            f"Обновлено занятий: {len(to_update)}."
        ))
        if unknown_codes:
            self.stdout.write(self.style.WARNING(
                "Неизвестные коды типов, занятия с ними не тронуты: "
                + ", ".join(sorted(unknown_codes))
            ))