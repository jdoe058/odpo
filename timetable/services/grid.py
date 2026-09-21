from dataclasses import dataclass
from collections import defaultdict
from datetime import date, timedelta
from django.db.models import Q, Sum

WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

@dataclass(frozen=True)
class GridDay:
    date: date
    weekday_ru: str
    is_weekend: bool


@dataclass(frozen=True)
class GridCell:
    date: date
    hours: int
    over_limit: bool


@dataclass(frozen=True)
class GridRow:
    employee: object
    cells: tuple[GridCell, ...]
    total: int

@dataclass(frozen=True)
class Grid:
    start: date
    end: date
    days: tuple[GridDay, ...]
    rows: tuple[GridRow, ...]


def calculate_grid(start: date, end: date, cycle=None, base=None) -> Grid:
    """
    Сетка «преподаватели × дни». Только типы занятий с counts_in_hours=True.
    Если cycle задан — только занятия этого цикла.
    Если base задан — только занятия, фактически проходящие на этой базе:
    Lesson.base=base либо (Lesson.base is null и Cycle.base=base).
    """
    from timetable.models import Employee, Lesson

    days_list = []
    d = start
    while d <= end:
        days_list.append(GridDay(
            date=d,
            weekday_ru=WEEKDAYS_RU[d.weekday()],
            is_weekend=d.weekday() >= 5,
        ))
        d += timedelta(days=1)

    qs = Lesson.objects.filter(
        date__gte=start,
        date__lte=end,
        lesson_type__counts_in_hours=True,
    )
    if cycle is not None:
        qs = qs.filter(cycle=cycle)
    if base is not None:
        qs = qs.filter(Q(base=base) | Q(base__isnull=True, cycle__base=base))

    rows_raw = list(qs.values("employee_id", "date").annotate(h=Sum("hours")))

    emp_ids = {r["employee_id"] for r in rows_raw}
    employees = list(
        Employee.objects.filter(pk__in=emp_ids).order_by("short_name")
    )

    agg: dict[int, dict[date, int]] = defaultdict(dict)
    for row in rows_raw:
        agg[row["employee_id"]][row["date"]] = row["h"]

    rows: list[GridRow] = []
    for emp in employees:
        cells = []
        total = 0
        for day in days_list:
            h = agg.get(emp.pk, {}).get(day.date, 0)
            over = emp.max_hours_per_day > 0 and h > emp.max_hours_per_day
            cells.append(GridCell(date=day.date, hours=h, over_limit=over))
            total += h
        rows.append(GridRow(employee=emp, cells=tuple(cells), total=total))

    return Grid(start=start, end=end, days=tuple(days_list), rows=tuple(rows))
