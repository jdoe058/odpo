from datetime import timedelta
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView

from timetable.exports.kinds import all_specs
from timetable.ped_hours_filter import PedHoursFilterForm, PedHoursFilterMixin
from timetable.schedule_filter import ScheduleFilterMixin, build_common_context
from timetable.services.cycle_hours import calculate_cycle_hours

from .cycle_xlsx_import import CycleImportError, import_cycle_from_xlsx
from .exports.cycle_xlsx_export import build_cycle_import_template
from .exports.ped_hours_xlsx import ped_hours_to_xlsx_bytes
from .forms import CycleImportForm
from .services.grid import calculate_grid
from .services.ped_hours import MONTH_NAMES_RU, calculate_ped_hours

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
