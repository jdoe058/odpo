from datetime import date, timedelta
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from timetable.services.cycle_hours import calculate_cycle_hours
from .services.periods import resolve_period

from .services.grid import calculate_grid
from .services.limits import calculate_overtime

from .forms import ScheduleImportForm, LessonForm
from .models import Cycle, Lesson, Base
from .imports import ScheduleImportError, import_schedule
from timetable.exports.kinds import all_specs

def schedule_import_view(request, admin_site):
    form = ScheduleImportForm()
    import_errors: list[str] = []

    if request.method == "POST":
        form = ScheduleImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = import_schedule(form.cleaned_data["file"])
            except ScheduleImportError as e:
                import_errors = e.errors
            else:
                messages.success(
                    request,
                    f"Импортировано занятий: {result.lessons_created}.",
                )
                return redirect(
                    "admin:timetable_cycle_change", result.cycle.pk
                )

    context = {
        **admin_site.each_context(request),
        "title": "Импорт расписания из XLSX",
        "opts": Cycle._meta,
        "form": form,
        "import_errors": import_errors,
    }
    return TemplateResponse(
        request, "timetable/schedule_import.html", context
    )

@login_required
def schedule_grid_view(request):
    period = request.GET.get("period", "week")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    cycle_id = request.GET.get("cycle")
    anchor_str = request.GET.get("anchor")
    base_id = request.GET.get("base") or ""

    cycle = None
    if cycle_id:
        cycle = (
            Cycle.objects
            .select_related("name", "base", "funding_type")
            .filter(pk=cycle_id)
            .first()
        )

    anchor = None
    if anchor_str:
        try:
            anchor = date.fromisoformat(anchor_str)
        except ValueError:
            anchor = None

    # Если якорь не задан явно — берём дату начала цикла (если он выбран)
    if anchor is None and cycle is not None:
        anchor = cycle.start_date

    try:
        if period in ("week", "month", "year"):
            start, end = resolve_period(period, anchor)
        elif period == "custom":
            start = date.fromisoformat(start_str) if start_str else None
            end = date.fromisoformat(end_str) if end_str else None
            start, end = resolve_period("custom", start=start, end=end)
        else:
            start, end = resolve_period(period)
    except (TypeError, ValueError):
        period = "week"
        start, end = resolve_period(period)

    grid = calculate_grid(start, end, cycle=cycle)
    overtime = calculate_overtime()

    lessons = []
    if cycle is not None:
        lessons = (
            cycle.lessons
            .select_related("lesson_type", "employee")
            .order_by("date", "time_start")
        )

    cycles = Cycle.objects.select_related("name", "base").order_by("-start_date")

    # анкеры для стрелок «←/→»
    prev_anchor = start - timedelta(days=1)
    next_anchor = end + timedelta(days=1)

    breakdown = calculate_cycle_hours(cycle) if cycle is not None else None

    return render(request, "timetable/schedule_grid.html", {
        "grid": grid,
        "overtime": overtime,
        "lessons": lessons,
        "period": period,
        "cycles": cycles,
        "selected_cycle": cycle,
        "export_kinds": all_specs(),
        "prev_anchor": prev_anchor,
        "next_anchor": next_anchor,
        "breakdown": breakdown,
        "selected_base": base_id,
        "bases": Base.objects.order_by("name"),
    })

@login_required
def lesson_edit_view(request, pk):
    lesson = get_object_or_404(
        Lesson.objects.select_related("cycle", "cycle__name"),
        pk=pk,
    )

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if lesson.cycle.in_archive:
        messages.error(request, "Цикл в архиве — редактирование запрещено.")
        return redirect(next_url or "timetable:schedule_grid")

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Занятие сохранено.")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("timetable:schedule_grid")
    else:
        form = LessonForm(instance=lesson)

    return render(request, "timetable/lesson_edit.html", {
        "form": form,
        "lesson": lesson,
        "next": next_url,
    })