"""
Разовая команда: заполняет group и category занятий по коду типа занятия.

Уже заполненные поля не трогаются. Работает по всем занятиям БД.
Аргументов не принимает.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from timetable.models import Lesson
from timetable.services.lesson_defaults import fill_empty_defaults


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

        changed = fill_empty_defaults(list(qs))
        if changed:
            Lesson.objects.bulk_update(changed, ["group", "category"])

        self.stdout.write(self.style.SUCCESS(
            f"Обновлено занятий: {len(changed)}."
        ))