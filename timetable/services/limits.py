from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from timetable.models import Employee, Lesson

SCOPES: tuple[str, ...] = ("day", "week", "year")
SCOPE_LABELS: dict[str, str] = {
    "day": "день",
    "week": "неделю",
    "year": "учебный год",
}
_SCOPE_ORDER = {s: i for i, s in enumerate(SCOPES)}

# --- Границы периодов ----------------------------------------------------

def _day_bounds(d: date) -> tuple[date, date]:
    return d, d


def _week_bounds(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def _year_bounds(d: date) -> tuple[date, date]:
    if d.month >= 9:
        return date(d.year, 9, 1), date(d.year + 1, 8, 31)
    return date(d.year - 1, 9, 1), date(d.year, 8, 31)

_BOUNDS = {
    "day": _day_bounds,
    "week": _week_bounds,
    "year": _year_bounds,
}

_LIMIT_ATTR = {
    "day": "max_hours_per_day",
    "week": "max_hours_per_week",
    "year": "max_hours_per_year",
}

# --- Результаты ----------------------------------------------------------

@dataclass(frozen=True)
class OvertimeItem:
    period_start: date
    period_end: date
    hours: int
    limit: int

    @property
    def excess(self) -> int:
        return self.hours - self.limit


@dataclass(frozen=True)
class OvertimeEmployee:
    employee: Employee
    scope: str
    items: tuple[OvertimeItem, ...]

    @property
    def total_excess(self) -> int:
        return sum(i.excess for i in self.items)

    @property
    def periods_count(self) -> int:
        return len(self.items)

    @property
    def limit(self) -> int:
        return self.items[0].limit

# --- Постфактум-мониторинг ----------------------------------------------

def calculate_overtime(
    scope: str,
    *,
    start: date | None = None,
    end: date | None = None,
) -> tuple[OvertimeEmployee, ...]:
    """
    Найти переработки в БД по заданному масштабу.

    Используется для UI-блока «Переработки»: при работающей валидации
    результат должен быть пустым; непустой результат сигнализирует
    об изменениях в обход (например, через админку).
    """
    if scope not in _BOUNDS:
        raise ValueError(f"unknown scope: {scope!r}")

    bounds_fn = _BOUNDS[scope]
    limit_attr = _LIMIT_ATTR[scope]

    qs = Lesson.objects.filter(lesson_type__counts_in_hours=True)
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lte=end)

    totals: dict[tuple[int, date], int] = defaultdict(int)
    period_end_by_key: dict[tuple[int, date], date] = {}

    for emp_id, d, h in qs.values_list("employee_id", "date", "hours"):
        p_start, p_end = bounds_fn(d)
        key = (emp_id, p_start)
        totals[key] += h
        period_end_by_key.setdefault(key, p_end)

    if not totals:
        return ()

    emp_ids = list({k[0] for k in totals})
    employees = {
        e.pk: e
        for e in Employee.objects
            .filter(pk__in=emp_ids)
            .select_related("position")
    }

    by_emp: dict[int, list[OvertimeItem]] = defaultdict(list)
    for (emp_id, p_start), hours in totals.items():
        emp = employees.get(emp_id)
        if emp is None:
            continue
        limit = getattr(emp, limit_attr)
        if not limit or hours <= limit:
            continue
        by_emp[emp_id].append(OvertimeItem(
            period_start=p_start,
            period_end=period_end_by_key[(emp_id, p_start)],
            hours=hours,
            limit=limit,
        ))

    result = [
        OvertimeEmployee(
            employee=employees[emp_id],
            scope=scope,
            items=tuple(sorted(items, key=lambda i: i.period_start)),
        )
        for emp_id, items in by_emp.items()
    ]
    result.sort(key=lambda o: (-o.total_excess, o.employee.short_name))
    return tuple(result)
