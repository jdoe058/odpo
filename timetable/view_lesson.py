"""Отдельная страница со списком занятий и фильтрами."""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min
from django.shortcuts import render

from .models import Base, Cycle, Lesson
from .services.employee_hours import resolve_period


@login_required
def lessons_list_view(request):
    period = request.GET.get("period", "week")
    start_str = request.GET.get("start") or ""
    end_str = request.GET.get("end") or ""
    cycle_id = request.GET.get("cycle") or ""
    base_id = request.GET.get("base") or ""

    bases = Base.objects.order_by("name")

    base = Base.objects.filter(pk=base_id).first() if base_id else None
    cycle = (
        Cycle.objects
        .select_related("name", "base", "funding_type")
        .filter(pk=cycle_id, base=base)
        .first()
        if (cycle_id and base is not None) else None
    )

    # База не выбрана — ничего не показываем.
    if base is None:
        return render(request, "timetable/lessons_list.html", {
            "bases": bases,
            "cycles": Cycle.objects.none(),
            "period": period,
            "start": None, "end": None,
            "start_str": start_str, "end_str": end_str,
            "selected_cycle": None,
            "selected_base": None,
            "lessons": [],
        })

    start = end = None
    try:
        if period == "custom":
            start = date.fromisoformat(start_str) if start_str else None
            end = date.fromisoformat(end_str) if end_str else None
            start, end = resolve_period("custom", start=start, end=end)
        elif period == "all":
            if cycle is not None:
                start, end = resolve_period("all", cycle=cycle)
            else:
                agg = (
                    Cycle.objects
                    .filter(base=base)
                    .aggregate(s=Min("start_date"), e=Max("end_date"))
                )
                start, end = agg["s"], agg["e"]
        else:
            start, end = resolve_period(period)
    except (TypeError, ValueError):
        period = "week"
        start, end = resolve_period(period)

    lessons_qs = (
        Lesson.objects
        .select_related(
            "cycle", "cycle__name", "cycle__base",
            "lesson_type", "employee",
        )
        .filter(cycle__base=base)
    )
    if start is not None and end is not None:
        lessons_qs = lessons_qs.filter(date__range=(start, end))
    if cycle is not None:
        lessons_qs = lessons_qs.filter(cycle=cycle)
    lessons_qs = lessons_qs.order_by("date", "time_start")

    cycles_qs = (
        Cycle.objects
        .select_related("name", "base")
        .filter(base=base)
        .order_by("-start_date")
    )

    return render(request, "timetable/lessons_list.html", {
        "lessons": lessons_qs,
        "bases": bases,
        "cycles": cycles_qs,
        "period": period,
        "start": start,
        "end": end,
        "start_str": start_str,
        "end_str": end_str,
        "selected_cycle": cycle,
        "selected_base": base,
    })

