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
class LimitViolation:
    """Превышение лимита: одна пара (сотрудник, масштаб, период)."""
    employee: Employee
    scope: str
    period_start: date
    period_end: date
    hours: int
    limit: int

    @property
    def excess(self) -> int:
        return self.hours - self.limit

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


# --- Pre-commit валидация -----------------------------------------------

def find_violations(
    lessons: Iterable,
    *,
    scope: str = "all",
    exclude_cycle_id: int | None = None,
    exclude_lesson_ids: Iterable[int] = (),
) -> tuple[LimitViolation, ...]:
    """
    Проверить, не превысят ли данные занятия лимиты по должности.

    :param lessons: iterable объектов с полями date, hours, employee,
        lesson_type. Подходят как Lesson, так и ParsedLesson.
    :param scope: "day" | "week" | "year" | "all".
    :param exclude_cycle_id: цикл, занятия которого будут удалены перед
        вставкой новых (сценарий переимпорта). Его занятия не учитываются
        как «уже в БД».
    :param exclude_lesson_ids: конкретные занятия, которые не учитывать
        (сценарий правки одного занятия: старая версия не должна
        считаться дважды).

    Не делает записей в БД.
    """
    new = [
        l for l in lessons
        if l.lesson_type.counts_in_hours and l.hours and l.hours > 0
    ]
    if not new:
        return ()

    scopes = SCOPES if scope == "all" else (scope,)
    for s in scopes:
        if s not in _BOUNDS:
            raise ValueError(f"unknown scope: {s!r}")

    emp_ids = {l.employee.pk for l in new}
    employees = {
        e.pk: e
        for e in Employee.objects
            .filter(pk__in=emp_ids)
            .select_related("position")
    }

    excluded_ids = tuple(exclude_lesson_ids)

    violations: list[LimitViolation] = []
    for s in scopes:
        violations.extend(_check_scope(
            s, new, employees,
            exclude_cycle_id=exclude_cycle_id,
            exclude_lesson_ids=excluded_ids,
        ))

    violations.sort(key=lambda v: (
        v.employee.short_name, _SCOPE_ORDER[v.scope], v.period_start,
    ))
    return tuple(violations)


@dataclass
class _Bucket:
    employee: Employee
    period_start: date
    period_end: date
    limit: int
    hours: int = 0


def _check_scope(
    scope: str,
    new_lessons: list,
    employees: dict[int, Employee],
    *,
    exclude_cycle_id: int | None,
    exclude_lesson_ids: tuple[int, ...],
) -> list[LimitViolation]:
    bounds_fn = _BOUNDS[scope]
    limit_attr = _LIMIT_ATTR[scope]

    buckets: dict[tuple[int, date], _Bucket] = {}

    for lesson in new_lessons:
        emp = employees.get(lesson.employee.pk)
        if emp is None:
            continue
        limit = getattr(emp, limit_attr)
        if not limit:
            continue
        p_start, p_end = bounds_fn(lesson.date)
        key = (emp.pk, p_start)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = buckets[key] = _Bucket(
                employee=emp, period_start=p_start, period_end=p_end,
                limit=limit,
            )
        bucket.hours += lesson.hours

    if not buckets:
        return []

    min_date = min(b.period_start for b in buckets.values())
    max_date = max(b.period_end for b in buckets.values())
    emp_ids = list({b.employee.pk for b in buckets.values()})

    qs = Lesson.objects.filter(
        lesson_type__counts_in_hours=True,
        date__range=(min_date, max_date),
        employee_id__in=emp_ids,
    )
    if exclude_cycle_id is not None:
        qs = qs.exclude(cycle_id=exclude_cycle_id)
    if exclude_lesson_ids:
        qs = qs.exclude(pk__in=exclude_lesson_ids)

    for emp_id, d, h in qs.values_list("employee_id", "date", "hours"):
        p_start, _ = bounds_fn(d)
        bucket = buckets.get((emp_id, p_start))
        if bucket is not None:
            bucket.hours += h

    return [
        LimitViolation(
            employee=b.employee, scope=scope,
            period_start=b.period_start, period_end=b.period_end,
            hours=b.hours, limit=b.limit,
        )
        for b in buckets.values()
        if b.hours > b.limit
    ]


def format_violation(v: LimitViolation) -> str:
    """Человекочитаемое сообщение о нарушении для форм и консоли."""
    if v.period_start == v.period_end:
        period = v.period_start.strftime("%d.%m.%Y")
    else:
        period = f"{v.period_start:%d.%m.%Y}–{v.period_end:%d.%m.%Y}"
    return (
        f"Превышение нагрузки за {SCOPE_LABELS[v.scope]}: "
        f"{v.employee.short_name} — {v.hours} ч ({period}), "
        f"лимит {v.limit} ч, переработка {v.excess} ч"
    )


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
