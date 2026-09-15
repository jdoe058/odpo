from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date
from typing import Iterable

MONTH_NAMES = (
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)

DAYS_IN_COLUMNS = 31


def _month_range(start: date, end: date) -> Iterable[tuple[int, int]]:
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _fmt(value: float) -> str:
    if not value:
        return ""
    return f"{value:g}"


def calculate_timesheet(cycle) -> list[dict]:
    lessons = (
        cycle.lessons
        .select_related("employee")
        .order_by("date", "time_start")
    )

    # Все преподаватели цикла — независимо от месяца.
    teachers: dict[int, object] = {}

    # (year, month) -> teacher_id -> day -> hours
    data: dict[tuple[int, int], dict[int, dict[int, float]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float)),
    )

    for lesson in lessons:
        teacher = lesson.employee
        teachers[teacher.pk] = teacher
        key = (lesson.date.year, lesson.date.month)
        data[key][teacher.pk][lesson.date.day] += float(lesson.hours or 0)

    ordered_teachers = sorted(
        teachers.values(), key=lambda t: t.short_name,
    )

    months: list[dict] = []
    for year, month in _month_range(cycle.start_date, cycle.end_date):
        days_in_month = monthrange(year, month)[1]
        by_teacher = data[(year, month)]

        rows: list[dict] = []
        for idx, teacher in enumerate(ordered_teachers, start=1):
            by_day = by_teacher.get(teacher.pk, {})
            total = 0.0
            cells: list[str] = []
            for d in range(1, DAYS_IN_COLUMNS + 1):
                if d <= days_in_month:
                    v = by_day.get(d, 0.0)
                    total += v
                    cells.append(_fmt(v))
                else:
                    cells.append("")
            rows.append({
                "n": idx,
                "teacher": teacher.short_name,
                "cells": cells,
                "total": _fmt(total) if total else "0",
            })

        months.append({
            "month_name": f"{MONTH_NAMES[month]} {year}",
            "rows": rows,
        })

    return months