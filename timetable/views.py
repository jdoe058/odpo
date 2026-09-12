from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from .forms import ScheduleImportForm
from .models import Cycle, Employee
from .services.cycle_hours import calculate_cycle_hours
from .services.employee_hours import calculate_employee_hours_all
from .services.schedule_import import ScheduleImportError, import_schedule

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

    if request.method == "POST":
        form = ScheduleImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = import_schedule(form.cleaned_data["file"])
            except ScheduleImportError as e:
                messages.error(request, str(e))
            else:
                messages.success(
                    request,
                    f"Импортировано занятий: {result.lessons_created}."
                )
                for w in result.warnings:
                    messages.warning(request, w)
                return redirect(
                    "admin:timetable_cycle_change", result.cycle.pk
                )

    context = {
        **admin_site.each_context(request),
        "title": "Импорт расписания из XLSX",
        "opts": Cycle._meta,
        "form": form,
    }
    from django.template.response import TemplateResponse
    return TemplateResponse(
        request, "timetable/schedule_import.html", context
    )