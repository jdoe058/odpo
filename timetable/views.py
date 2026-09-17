from datetime import date, timedelta
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from .services.cycle_hours import calculate_cycle_hours
from .services.employee_hours import (
    resolve_period, 
    calculate_grid,   
    calculate_overtime, 
    calculate_employee_hours_all, 
)
from .forms import ScheduleImportForm
from .models import Cycle, Employee
from .imports import ScheduleImportError, import_schedule
from timetable.exports.kinds import all_specs

def employee_hours_report(request, employee_id, admin_site):
    """Отдельная страница отчёта по часам сотрудника."""
    employee = get_object_or_404(Employee, pk=employee_id)
    data = calculate_employee_hours_all(employee)

    context = {
        **admin_site.each_context(request),
        "title": f"Часы: {employee.short_name}",
        "opts": Employee._meta,
        "employee": employee,
        "data": data,
    }
    return TemplateResponse(
        request,
        "timetable/employee_hours_report.html",
        context,
    )

def cycle_hours_report(request, cycle_id, admin_site):
    """Отдельная страница отчёта по часам цикла."""
    cycle = get_object_or_404(Cycle, pk=cycle_id)
    data = calculate_cycle_hours(cycle)

    context = {
        **admin_site.each_context(request),
        "title": f"Часы: {cycle.name}",
        "opts": Cycle._meta,
        "cycle": cycle,
        "data": data,
    }
    return TemplateResponse(
        request,
        "timetable/cycle_hours_report.html",
        context,
    )

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

from datetime import date, timedelta
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from .services.cycle_hours import calculate_cycle_hours
from .services.employee_hours import (
    resolve_period,
    calculate_grid,
    calculate_overtime,
    calculate_employee_hours_all,
)
from .forms import ScheduleImportForm
from .models import Cycle, Employee
from .imports import ScheduleImportError, import_schedule
from timetable.exports.kinds import all_specs


def _shift_period(period: str, anchor: date):
    """Границы недели/месяца, содержащего anchor."""
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())  # Пн
        end = start + timedelta(days=6)                    # Вс
        return start, end
    if period == "month":
        start = anchor.replace(day=1)
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1)
        else:
            nxt = start.replace(month=start.month + 1)
        end = nxt - timedelta(days=1)
        return start, end
    return None


@login_required
def schedule_grid_view(request):
    period = request.GET.get("period", "week")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    cycle_id = request.GET.get("cycle")
    anchor_str = request.GET.get("anchor")

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

    try:
        if period in ("week", "month") and anchor:
            start, end = _shift_period(period, anchor)
        elif period == "custom":
            start = date.fromisoformat(start_str) if start_str else None
            end = date.fromisoformat(end_str) if end_str else None
            start, end = resolve_period("custom", start=start, end=end)
        elif period == "all":
            start, end = resolve_period("all", cycle=cycle)
        else:
            start, end = resolve_period(period)
    except (TypeError, ValueError):
        period = "week"
        start, end = resolve_period(period)

    grid = calculate_grid(start, end, cycle=cycle)
    overtime = calculate_overtime()
    cycles = Cycle.objects.select_related("name", "base").order_by("-start_date")

    # анкеры для стрелок «←/→»
    prev_anchor = start - timedelta(days=1)
    next_anchor = end + timedelta(days=1)

    return render(request, "timetable/schedule_grid.html", {
        "grid": grid,
        "overtime": overtime,
        "period": period,
        "cycles": cycles,
        "selected_cycle": cycle,
        "export_kinds": all_specs(),
        "prev_anchor": prev_anchor,
        "next_anchor": next_anchor,
    })
