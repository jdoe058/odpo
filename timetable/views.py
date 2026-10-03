from datetime import date, timedelta
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from timetable.exports.kinds import all_specs
from timetable.schedule_filter import (
    ScheduleFilterMixin, filter_cycles, filter_lessons,
)
from timetable.services.cycle_hours import calculate_cycle_hours

from .cycle_xlsx_import import CycleImportError, import_cycle_from_xlsx
from .exports.cycle_xlsx_export import build_cycle_import_template
from .exports.ped_hours_xlsx import ped_hours_to_xlsx_bytes
from .forms import CycleImportForm, LessonForm, PedHoursFilterForm
from .models import Base, Cycle, Lesson
from .services.grid import calculate_grid
from .services.limits import (
    SCOPE_LABELS, calculate_overtime, find_violations, format_violation,
)
from .services.ped_hours import MONTH_NAMES_RU, calculate_ped_hours

class ScheduleGrid(LoginRequiredMixin, ScheduleFilterMixin, TemplateView):
    template_name = "timetable/schedule_grid.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data = self.filter_data

        start = data["resolved_start"]
        end = data["resolved_end"]
        cycle = data.get("cycle")
        base = data.get("base")

        grid = calculate_grid(
            start, end, cycle=cycle, base=base,
            employee_q=data["employee_q"],
        )

        overtime = []
        for scope in ("day", "week", "year"):
            items = calculate_overtime(scope)
            if items:
                overtime.append((SCOPE_LABELS[scope], items))

        lessons = []
        if cycle is not None:
            qs = (
                Lesson.objects
                .filter(cycle=cycle)
                .select_related("lesson_type", "employee", "cycle", "cycle__name")
                .order_by("date", "time_start")
            )
            lessons = filter_lessons(qs, data)
        elif base is not None or data["employee_query"]:
            qs = (
                Lesson.objects
                .filter(date__gte=start, date__lte=end)
                .select_related(
                    "lesson_type", "employee", "cycle", "cycle__name", "base",
                )
                .order_by("date", "time_start")
            )
            lessons = filter_lessons(qs, data)

        cycles_qs = (
            Cycle.objects
            .select_related("name", "base")
            .order_by("-start_date")
        )
        cycles = filter_cycles(cycles_qs, data)

        breakdown = (
            calculate_cycle_hours(cycle) if cycle is not None else None
        )

        ctx.update({
            "form": self.filter_form,
            "grid": grid,
            "overtime": overtime,
            "lessons": lessons,
            "period": data["period"],
            "cycles": cycles,
            "selected_cycle": cycle,
            "export_kinds": all_specs(),
            "prev_anchor": start - timedelta(days=1),
            "next_anchor": end + timedelta(days=1),
            "breakdown": breakdown,
            "selected_employee": data["employee_query"],
            "bases": Base.objects.order_by("name"),
        })
        return ctx
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
def cycle_import_view(request):
    errors: list[str] = []
    form = CycleImportForm()

    if request.method == "POST":
        form = CycleImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                cycle = import_cycle_from_xlsx(form.cleaned_data["file"])
            except CycleImportError as e:
                errors = e.errors
            else:
                messages.success(
                    request,
                    f"Импортирован цикл «{cycle.name.name}» "
                    f"от {cycle.start_date:%d.%m.%Y}.",
                )
                url = reverse("timetable:schedule_grid")
                return redirect(f"{url}?cycle={cycle.pk}")

    return render(request, "timetable/cycle_import.html", {
        "form": form,
        "errors": errors,
    })

@login_required
def cycle_import_template_view(request):
    content = build_cycle_import_template()
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="cycle_import_template.xlsx"'
    )
    return response

@login_required
def ped_hours_view(request):
    today = date.today()
    form = PedHoursFilterForm(request.GET or None)

    if form.is_valid():
        year = int(form.cleaned_data["year"])
        month = int(form.cleaned_data["month"])
    else:
        year, month = today.year, today.month
        form = PedHoursFilterForm(initial={"year": year, "month": month})

    report = calculate_ped_hours(year, month)

    return render(request, "timetable/reports/ped_hours.html", {
        "report": report,
        "form": form,
        "month_label": f"{MONTH_NAMES_RU[month]} {year}",
    })

@login_required
def ped_hours_export_view(request):
    today = date.today()
    form = PedHoursFilterForm(request.GET or None)

    if form.is_valid():
        year = int(form.cleaned_data["year"])
        month = int(form.cleaned_data["month"])
    else:
        year, month = today.year, today.month

    report = calculate_ped_hours(year, month)
    content = ped_hours_to_xlsx_bytes(report)

    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
    filename = f"ped_hours_{year:04d}-{month:02d}.xlsx"
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return response
