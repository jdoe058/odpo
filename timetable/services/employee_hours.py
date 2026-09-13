from dataclasses import dataclass
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone


WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


@dataclass(frozen=True)
class DayHours:
    date: date
    hours: int
    over_limit: bool

    @property
    def weekday_ru(self) -> str:
        return WEEKDAYS_RU[self.date.weekday()]


@dataclass(frozen=True)
class EmployeeHours:
    start: date
    end: date
    days: tuple[DayHours, ...]
    total: int
    max_per_day: int
    days_over_limit: int


def resolve_period(kind, today=None, start=None, end=None):
    """kind: 'week' | 'month' | 'custom' → (start, end)."""
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


def calculate_employee_hours(employee, start, end) -> EmployeeHours:
    """
    Часы по дням за период. Только типы занятий с counts_in_hours=True.
    Дни без занятий в результат не попадают.
    """
    from timetable.models import Lesson

    rows = (
        Lesson.objects
        .filter(
            employee=employee,
            date__gte=start,
            date__lte=end,
            lesson_type__counts_in_hours=True,
        )
        .values("date")
        .annotate(hours=Sum("hours"))
        .order_by("date")
    )

    max_per_day = employee.max_hours_per_day
    days, over_count = [], 0
    for row in rows:
        h = row["hours"] or 0
        over = max_per_day > 0 and h > max_per_day
        over_count += int(over)
        days.append(DayHours(date=row["date"], hours=h, over_limit=over))

    return EmployeeHours(
        start=start, end=end,
        days=tuple(days),
        total=sum(d.hours for d in days),
        max_per_day=max_per_day,
        days_over_limit=over_count,
    )

def calculate_employee_hours_all(employee) -> EmployeeHours:
    """
    Часы по дням за всё время. Только типы занятий с counts_in_hours=True.
    """
    from timetable.models import Lesson

    rows = (
        Lesson.objects
        .filter(
            employee=employee,
            lesson_type__counts_in_hours=True,
        )
        .values("date")
        .annotate(hours=Sum("hours"))
        .order_by("date")
    )

    max_per_day = employee.max_hours_per_day
    days, over_count = [], 0
    for row in rows:
        h = row["hours"] or 0
        over = max_per_day > 0 and h > max_per_day
        over_count += int(over)
        days.append(DayHours(date=row["date"], hours=h, over_limit=over))

    dates = [d.date for d in days] or [None]
    return EmployeeHours(
        start=dates[0],
        end=dates[-1],
        days=tuple(days),
        total=sum(d.hours for d in days),
        max_per_day=max_per_day,
        days_over_limit=over_count,
    )


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
class OverEvent:
    employee: object
    date: date
    hours: int
    limit: int


@dataclass(frozen=True)
class Grid:
    start: date
    end: date
    days: tuple[GridDay, ...]
    rows: tuple[GridRow, ...]
    over_events: tuple[OverEvent, ...]


def calculate_grid(start: date, end: date) -> Grid:
    """
    Сетка «преподаватели × дни». Только типы занятий с counts_in_hours=True.
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

    employees = list(Employee.objects.order_by("short_name"))

    qs = (
        Lesson.objects
        .filter(
            date__gte=start,
            date__lte=end,
            lesson_type__counts_in_hours=True,
        )
        .values("employee_id", "date")
        .annotate(h=Sum("hours"))
    )

    agg: dict[int, dict[date, int]] = defaultdict(dict)
    for row in qs:
        agg[row["employee_id"]][row["date"]] = row["h"]

    rows: list[GridRow] = []
    over_events: list[OverEvent] = []

    for emp in employees:
        cells = []
        total = 0
        for day in days_list:
            h = agg.get(emp.pk, {}).get(day.date, 0)
            over = emp.max_hours_per_day > 0 and h > emp.max_hours_per_day
            cells.append(GridCell(date=day.date, hours=h, over_limit=over))
            total += h
            if over:
                over_events.append(OverEvent(
                    employee=emp,
                    date=day.date,
                    hours=h,
                    limit=emp.max_hours_per_day,
                ))
        rows.append(GridRow(employee=emp, cells=tuple(cells), total=total))

    return Grid(
        start=start, end=end,
        days=tuple(days_list),
        rows=tuple(rows),
        over_events=tuple(over_events),
    )

