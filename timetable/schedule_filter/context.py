"""Сборка общего контекста для страниц расписания."""
from datetime import timedelta

from timetable.models import Base, Cycle
from timetable.services.limits import SCOPE_LABELS, calculate_overtime

from .apply import filter_cycles


def build_common_context(view) -> dict:
    """
    Общий набор переменных для ScheduleGrid и ScheduleLessons:
    форма фильтра, overtime, список циклов, границы периода.
    """
    data = view.filter_data
    start = data["resolved_start"]
    end = data["resolved_end"]
    base = data.get("base")
    cycle = data.get("cycle")

    overtime = []
    for scope in ("day", "week", "year"):
        items = calculate_overtime(scope)
        if items:
            overtime.append((SCOPE_LABELS[scope], items))

    cycles_qs = (
        Cycle.objects
        .select_related("name", "base")
        .order_by("-start_date")
    )
    cycles = filter_cycles(cycles_qs, data)

    return {
        "form": view.filter_form,
        "period": data["period"],
        "start": start,
        "end": end,
        "base": base,
        "cycle": cycle,
        "overtime": overtime,
        "cycles": cycles,
        "selected_cycle": cycle,
        "selected_employee": data["employee_query"],
        "prev_anchor": start - timedelta(days=1),
        "next_anchor": end + timedelta(days=1),
        "bases": Base.objects.order_by("name"),
    }