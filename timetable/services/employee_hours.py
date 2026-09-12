from dataclasses import dataclass
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