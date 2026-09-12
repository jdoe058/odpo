from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Prefetch


@dataclass(frozen=True)
class TypeBreakdown:
    """Часы по одному типу занятия."""
    code: str
    name: str
    sort_order: int
    hours: int


@dataclass(frozen=True)
class CycleHours:
    """Итог по циклу: общее число часов и разбивка по типам."""
    total: int
    by_type: tuple[TypeBreakdown, ...]


def calculate_cycle_hours(cycle) -> CycleHours:
    """
    Считает часы цикла по занятиям, у которых lesson_type.counts_in_hours=True.

    Если lessons предзагружены через prefetch_lessons_for_hours(),
    функция работает без дополнительных SQL-запросов.
    """
    totals: dict[int, int] = defaultdict(int)
    types: dict[int, object] = {}

    for lesson in cycle.lessons.all():
        lt = lesson.lesson_type
        if not lt.counts_in_hours:
            continue
        totals[lt.pk] += lesson.hours
        types[lt.pk] = lt

    by_type = tuple(
        sorted(
            (
                TypeBreakdown(
                    code=lt.code,
                    name=lt.name,
                    sort_order=lt.sort_order,
                    hours=totals[lt.pk],
                )
                for lt in types.values()
            ),
            key=lambda b: b.sort_order,
        )
    )

    return CycleHours(total=sum(totals.values()), by_type=by_type)


def prefetch_lessons_for_hours(queryset):
    """
    Оптимизация для списков: подгружает lessons + lesson_type одним запросом,
    чтобы calculate_cycle_hours не бил по БД на каждый цикл.
    """
    from timetable.models import Lesson  # локальный импорт — избегаем циклов

    return queryset.prefetch_related(
        Prefetch(
            "lessons",
            queryset=Lesson.objects.select_related("lesson_type"),
        )
    )