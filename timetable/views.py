from datetime import date, timedelta
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, UpdateView

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
    

class LessonEdit(LoginRequiredMixin, UpdateView):
    """Редактирование занятия."""

    model = Lesson
    form_class = LessonForm
    template_name = "timetable/lesson_edit.html"

    def get_queryset(self):
        return Lesson.objects.select_related("cycle", "cycle__name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lesson"] = self.get_object()
        ctx["next"] = self._next_url()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Занятие сохранено.")
        return response

    def get_success_url(self):
        next_url = self._next_url()
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()},
        ):
            return next_url
        return reverse("timetable:schedule_grid")

    def _next_url(self):
        return (
            self.request.GET.get("next")
            or self.request.POST.get("next")
            or ""
        )

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
