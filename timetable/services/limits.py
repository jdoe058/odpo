from typing import TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict
from datetime import date
from django.db.models import Sum

if TYPE_CHECKING:
    from timetable.models import Employee


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

