from collections import defaultdict

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from timetable.exports.forms import DocumentTemplateForm
from timetable.exports.models import DocumentTemplate

from datetime import date, timedelta
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from timetable.services.cycle_hours import calculate_cycle_hours
from .services.periods import resolve_period
from .services.grid import calculate_grid
from .services.limits import (
    SCOPE_LABELS, calculate_overtime, find_violations, format_violation,
)

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
    base = None
    if base_id:
        base = Base.objects.filter(pk=base_id).first()
        if base is None:
            base_id = ""

    anchor = None
    if anchor_str:
        try:
            anchor = date.fromisoformat(anchor_str)
        except ValueError:
            anchor = None

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

    grid = calculate_grid(start, end, cycle=cycle, base=base)

    overtime = []
    for scope in ("day", "week", "year"):
        items = calculate_overtime(scope)
        if items:
            overtime.append((SCOPE_LABELS[scope], items))

    lessons = []
    if cycle is not None:
        qs = (
            cycle.lessons
            .select_related("lesson_type", "employee")
            .order_by("date", "time_start")
        )
        if base is not None:
            qs = qs.filter(Q(base=base) | Q(base__isnull=True, cycle__base=base))
        lessons = qs

    cycles_qs = Cycle.objects.select_related("name", "base").order_by("-start_date")
    if base is not None:
        cycles_qs = cycles_qs.filter(base=base)
    cycles = cycles_qs

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
            candidate = form.save(commit=False)
            violations = find_violations(
                [candidate],
                exclude_lesson_ids=(candidate.pk,) if candidate.pk else (),
            )
            if violations:
                for v in violations:
                    messages.error(request, format_violation(v))
            else:
                candidate.save()
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

@login_required
def template_library_view(request):
    """
    Страница управления шаблонами: форма загрузки сверху, ниже —
    список всех версий, сгруппированный по видам. Рабочим считается
    последний загруженный шаблон (см. library.get_latest_template).

    POST может приходить двумя путями:
    * обычной формой (без JS) — отвечаем redirect с messages;
    * через Dropzone (AJAX) — отвечаем JSON, JS сам перезагрузит
      страницу после успеха.
    """
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    form = DocumentTemplateForm()

    if request.method == "POST":
        form = DocumentTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            tpl = form.save(commit=False)
            tpl.uploaded_by = request.user
            tpl.save()
            if is_ajax:
                return JsonResponse({"status": "ok"})
            messages.success(request, "Шаблон загружен.")
            return redirect("timetable:template_library")

        if is_ajax:
            return JsonResponse(
                {"status": "error", "errors": form.errors.get_json_data()},
                status=400,
            )
        messages.error(request, "Исправьте ошибки в форме.")

    return render(request, "timetable/template_library.html", {
        "form": form,
        "groups": _group_templates_by_kind(),
    })


def _group_templates_by_kind() -> list[dict]:
    by_kind: dict[str, list[DocumentTemplate]] = defaultdict(list)
    qs = (
        DocumentTemplate.objects
        .select_related("uploaded_by")
        .order_by("-uploaded_at")
    )
    for tpl in qs:
        by_kind[tpl.kind].append(tpl)
    return [
        {"spec": spec, "templates": by_kind.get(spec.code, [])}
        for spec in all_specs()
    ]


@login_required
@require_POST
def template_delete_view(request, pk):
    tpl = get_object_or_404(DocumentTemplate, pk=pk)
    kind = tpl.kind
    latest = (
        DocumentTemplate.objects
        .filter(kind=kind)
        .order_by("-uploaded_at")
        .first()
    )
    was_latest = latest is not None and latest.pk == tpl.pk

    tpl.file.delete(save=False)
    tpl.delete()

    if was_latest:
        messages.warning(
            request,
            f"Удалён рабочий шаблон «{kind}». Экспорт этого вида "
            "будет недоступен, пока не загрузите новый.",
        )
    else:
        messages.success(request, "Шаблон удалён.")
    return redirect("timetable:template_library")
