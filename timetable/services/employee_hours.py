from typing import TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict
from datetime import date, timedelta
from django.db.models import Max, Min, Sum
from django.utils import timezone

if TYPE_CHECKING:
    from timetable.models import Employee

WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def resolve_period(kind, today=None, start=None, end=None, cycle=None):
    """kind: 'week' | 'month' | 'custom' | 'all' → (start, end)."""
    from timetable.models import Lesson

    if kind == "all":
        if cycle is not None:
            return cycle.start_date, cycle.end_date

        qs = Lesson.objects.all()
        agg = qs.aggregate(first=Min("date"), last=Max("date"))
        if agg["first"] and agg["last"]:
            return agg["first"], agg["last"]

        # если занятий нет — текущая неделя
        today = today or timezone.localdate()
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    today = today or timezone.localdate()

    if kind == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    if kind == "month":
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return start, end

    if kind == "custom":
        if not start or not end:
            raise ValueError("custom period requires start and end")
        if end < start:
            start, end = end, start
        return start, end

    raise ValueError(f"unknown period kind: {kind!r}")

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


def calculate_grid(start: date, end: date, cycle=None) -> Grid:
    """
    Сетка «преподаватели × дни». Только типы занятий с counts_in_hours=True.
    Если cycle задан — только занятия этого цикла.
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

@dataclass(frozen=True)
class OverDay:
    date: date
    hours: int
    excess: int


@dataclass(frozen=True)
class OvertimeEmployee:
    employee: "Employee"
    limit: int
    days: tuple[OverDay, ...]
    total_excess: int

    @property
    def days_count(self) -> int:
        return len(self.days)


def calculate_overtime(start: date | None = None, end: date | None = None) -> tuple[OvertimeEmployee, ...]:
    """
    Переработки: только типы занятий с counts_in_hours=True,
    только сотрудники с max_hours_per_day > 0.
    Если start/end не заданы — считает за всё время.
    Возвращает список, отсортированный по убыванию суммарной переработки.
    """
    from timetable.models import Employee, Lesson

    qs = Lesson.objects.filter(lesson_type__counts_in_hours=True)
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lte=end)

    rows = (
        qs.values("employee_id", "date")
        .annotate(h=Sum("hours"))
    )

    by_emp: dict[int, list[tuple[date, int]]] = defaultdict(list)
    for row in rows:
        by_emp[row["employee_id"]].append((row["date"], row["h"]))

    if not by_emp:
        return ()

    employees = {e.pk: e for e in Employee.objects.filter(pk__in=by_emp.keys())}

    result: list[OvertimeEmployee] = []
    for emp_id, items in by_emp.items():
        emp = employees.get(emp_id)
        if emp is None or emp.max_hours_per_day <= 0:
            continue

        days: list[OverDay] = []
        total_excess = 0
        for d, h in sorted(items, key=lambda x: x[0]):
            if h > emp.max_hours_per_day:
                excess = h - emp.max_hours_per_day
                days.append(OverDay(date=d, hours=h, excess=excess))
                total_excess += excess

        if days:
            result.append(OvertimeEmployee(
                employee=emp,
                limit=emp.max_hours_per_day,
                days=tuple(days),
                total_excess=total_excess,
            ))

    result.sort(key=lambda o: (-o.total_excess, o.employee.short_name))
    return tuple(result)

