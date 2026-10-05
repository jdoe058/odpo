"""Отчёт «Распределение педагогических часов за месяц»."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from django.db.models import Min, Sum

from timetable.models import Cycle


@dataclass(frozen=True)
class PedHoursRow:
    """Одна строка отчёта — один цикл."""
    hours: int
    cycle_name: str
    start_date: date
    end_date: date
    compiled_by: str
    base: str
    funding: str


@dataclass(frozen=True)
class PedHoursTotal:
    """Итог по одному заведующему."""
    compiled_by: str
    hours: int


@dataclass(frozen=True)
class PedHoursReport:
    """Отчёт за месяц целиком."""
    year: int
    month: int
    rows: tuple[PedHoursRow, ...]
    totals: tuple[PedHoursTotal, ...]
    total_hours: int
    total_cycles: int


MONTH_NAMES_RU = (
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Первое и последнее число месяца."""
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)

def available_years() -> list[int]:
    """
    Годы для селекта: от минимального года цикла до текущего+1.
    Минимум 5 лет в списке, даже если циклов мало.
    """
    today = date.today()
    min_date = Cycle.objects.aggregate(m=Min("start_date"))["m"]
    start = min_date.year if min_date else today.year - 2
    start = min(start, today.year - 2)
    end = max(today.year + 1, start + 4)
    return list(range(start, end + 1))

def calculate_ped_hours(year: int, month: int, funding=None) -> PedHoursReport:
    """
    Отчёт за месяц: циклы, чей период пересекается с месяцем.

    Пед. часы цикла — сумма часов ВСЕХ занятий, независимо от типа
    и от флага counts_in_hours. Экзамены и консультации тоже считаются.
    """
    start, end = month_bounds(year, month)

    cycles = (
        Cycle.objects
        .filter(start_date__lte=end, end_date__gte=start)
        .select_related("name", "base", "funding_type", "compiled_by")
        .annotate(total_hours=Sum("lessons__hours"))
    )
    if funding is not None:
        cycles = cycles.filter(funding_type=funding)

    rows = [
        PedHoursRow(
            hours=getattr(c, "total_hours", 0) or 0,
            cycle_name=c.name.name,
            start_date=c.start_date,
            end_date=c.end_date,
            compiled_by=c.compiled_by.short_name,
            base=c.base.name,
            funding=c.funding_type.name,
        )
        for c in cycles
    ]
    rows.sort(key=lambda r: (r.start_date, r.cycle_name))

    totals_map: dict[str, int] = {}
    for r in rows:
        totals_map[r.compiled_by] = totals_map.get(r.compiled_by, 0) + r.hours
    totals = tuple(
        PedHoursTotal(compiled_by=name, hours=hours)
        for name, hours in sorted(totals_map.items())
    )

    return PedHoursReport(
        year=year,
        month=month,
        rows=tuple(rows),
        totals=totals,
        total_hours=sum(r.hours for r in rows),
        total_cycles=len(rows),
    )