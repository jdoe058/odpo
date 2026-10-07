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
    ScheduleFilterMixin, build_common_context, filter_lessons,
)
from timetable.services.cycle_hours import calculate_cycle_hours

from .cycle_xlsx_import import CycleImportError, import_cycle_from_xlsx
from .exports.cycle_xlsx_export import build_cycle_import_template
from .exports.ped_hours_xlsx import ped_hours_to_xlsx_bytes
from .forms import CycleImportForm, LessonForm
from .models import Lesson
from .services.grid import calculate_grid
from .services.limits import (
    find_violations, format_violation,
)
from .services.ped_hours import MONTH_NAMES_RU, calculate_ped_hours
from .ped_hours_filter import PedHoursFilterForm, PedHoursFilterMixin

class ScheduleGrid(LoginRequiredMixin, ScheduleFilterMixin, TemplateView):
    template_name = "timetable/schedule_grid.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(build_common_context(self))

        data = self.filter_data
        cycle = data.get("cycle")

        grid = calculate_grid(
            ctx["start"], ctx["end"],
            cycle=cycle, base=data.get("base"),
            employee_q=data["employee_q"],
        )
        breakdown = (
            calculate_cycle_hours(cycle) if cycle is not None else None
        )

        ctx.update({
            "grid": grid,
            "breakdown": breakdown,
            "export_kinds": all_specs(),
        })
        return ctx


class ScheduleLessons(LoginRequiredMixin, ScheduleFilterMixin, TemplateView):
    template_name = "timetable/schedule_lessons.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(build_common_context(self))

        data = self.filter_data
        cycle = data.get("cycle")
        base = data.get("base")

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
                .filter(date__gte=ctx["start"], date__lte=ctx["end"])
                .select_related(
                    "lesson_type", "employee", "cycle", "cycle__name", "base",
                )
                .order_by("date", "time_start")
            )
            lessons = filter_lessons(qs, data)

        ctx.update({
            "lessons": lessons,
            "export_kinds": all_specs(),
        })
        return ctx
    

@login_required
def lesson_edit_view(request, pk):
    lesson = get_object_or_404(
        Lesson.objects.select_related("cycle", "cycle__name"),
        pk=pk,
    )

    next_url = request.GET.get("next") or request.POST.get("next") or ""

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


class PedHoursReport(LoginRequiredMixin, PedHoursFilterMixin, TemplateView):
    template_name = "timetable/reports/ped_hours.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        year = self.filter_data["year"]
        month = self.filter_data["month"]
        funding = self.filter_data.get("funding")

        report = calculate_ped_hours(year, month, funding=funding)

        ctx.update({
            "form": self.filter_form,
            "report": report,
            "month_label": f"{MONTH_NAMES_RU[month]} {year}",
        })
        return ctx


@login_required
def ped_hours_export_view(request):
    form = PedHoursFilterForm(request.GET)
    form.is_valid()
    year = form.cleaned_data["year"]
    month = form.cleaned_data["month"]
    funding = form.cleaned_data.get("funding")

    report = calculate_ped_hours(year, month, funding=funding)
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
