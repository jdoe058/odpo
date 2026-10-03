"""Применение фильтра расписания к queryset'ам."""
from django.db.models import Q


def filter_lessons(qs, data: dict):
    """
    Накладывает фильтры на queryset занятий:
    cycle, base, employee_q.

    Не трогает даты — период накладывает потребитель,
    потому что для цикла и для периода правила разные.
    """
    cycle = data.get("cycle")
    base = data.get("base")
    employee_q = data.get("employee_q")

    if cycle is not None:
        qs = qs.filter(cycle=cycle)
    if base is not None:
        qs = qs.filter(Q(base=base) | Q(base__isnull=True, cycle__base=base))
    if employee_q:
        qs = qs.filter(employee_q)
    return qs


def filter_cycles(qs, data: dict):
    """Обрезает список циклов под выбранную базу."""
    base = data.get("base")
    if base is not None:
        qs = qs.filter(base=base)
    return qs