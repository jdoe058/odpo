from io import BytesIO
from docxtpl import DocxTemplate
from datetime import date
from urllib.parse import quote

from django.http import HttpResponse, Http404
from django.contrib import messages
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from .forms import ScheduleImportForm
from .models import Cycle, Employee, DocumentTemplate
from .services.cycle_hours import calculate_cycle_hours
from .services.schedule_import import ScheduleImportError, import_schedule

from .services.employee_hours import (
    calculate_employee_hours_all, calculate_grid, 
    resolve_period, calculate_overtime, resolve_period,
)

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

def schedule_grid_view(request):
    period = request.GET.get("period", "week")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    try:
        if period == "custom":
            start = date.fromisoformat(start_str) if start_str else None
            end = date.fromisoformat(end_str) if end_str else None
            start, end = resolve_period("custom", start=start, end=end)
        else:
            start, end = resolve_period(period)
    except (TypeError, ValueError):
        period = "week"
        start, end = resolve_period(period)

    grid = calculate_grid(start, end)

    return render(request, "timetable/schedule_grid.html", {
        "grid": grid,
        "period": period,
    })

def _resolve_request_period(request):
    period = request.GET.get("period", "week")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    try:
        if period == "custom":
            start = date.fromisoformat(start_str) if start_str else None
            end = date.fromisoformat(end_str) if end_str else None
            start, end = resolve_period("custom", start=start, end=end)
        else:
            start, end = resolve_period(period)
    except (TypeError, ValueError):
        period = "week"
        start, end = resolve_period(period)

    return start, end, period

def schedule_grid_view(request):
    start, end, period = _resolve_request_period(request)
    grid = calculate_grid(start, end)
    overtime = calculate_overtime()

    return render(request, "timetable/schedule_grid.html", {
        "grid": grid,
        "overtime": overtime,
        "period": period,
    })

def overtime_view(request):
    """Отдельная страница только с переработками."""
    start, end, period = _resolve_request_period(request)
    overtime = calculate_overtime(start, end)

    return render(request, "timetable/_overtime_block.html", {
        "overtime": overtime,
        "period": period,
    })

def cycle_export_docx(request, cycle_id, admin_site):
    cycle = get_object_or_404(
        Cycle.objects.select_related(
            "name", "funding_type", "base", "compiled_by"
        ),
        pk=cycle_id,
    )

    tpl_record = DocumentTemplate.objects.filter(
        kind__code="schedule",
        is_active=True,
    ).first()
    if tpl_record is None:
        raise Http404("Активный шаблон расписания не загружен. "
                      "Загрузите его в разделе «Шаблоны документов».")

    lessons = (
        cycle.lessons
        .select_related("lesson_type", "employee")
        .order_by("date", "time_start")
    )
    hours = calculate_cycle_hours(cycle)

    lessons_ctx = [
        {
            "date": lesson.date.strftime("%d.%m.%Y"),
            "time": (
                f"{lesson.time_start.strftime('%H:%M')}-"
                f"{lesson.time_end.strftime('%H:%M')}"
            ),
            "type": lesson.lesson_type.name,
            "hours": lesson.hours,
            "topic": lesson.topic,
            "teacher": lesson.employee.short_name,
        }
        for lesson in lessons
    ]

    tpl = DocxTemplate(tpl_record.file.path)
    tpl.render({
        "cycle_name": cycle.name.name,
        "funding": cycle.funding_type.name if cycle.funding_type else "",
        "start": cycle.start_date.strftime("%d.%m.%Y"),
        "end": cycle.end_date.strftime("%d.%m.%Y"),
        "base": cycle.base.name,
        "compiled_by": cycle.compiled_by.short_name,
        "lessons": lessons_ctx,
        "hours_summary": hours.by_type,
        "total_hours": hours.total,
    })

    buf = BytesIO()
    tpl.save(buf)
    buf.seek(0)

    filename = f"Расписание_{cycle.name.name}_{cycle.start_date:%Y-%m-%d}.docx"
    response = HttpResponse(
        buf.read(),
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return response