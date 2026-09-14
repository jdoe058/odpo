from django.http import HttpResponse

from timetable.exports.base import (
    get_active_template, render_docx, docx_response,
)
from timetable.services.cycle_hours import calculate_cycle_hours


def build_schedule_context(cycle) -> dict:
    """Контекст для шаблона расписания. Чистая функция — тестируется без БД."""
    lessons = (
        cycle.lessons
        .select_related("lesson_type", "employee")
        .order_by("date", "time_start")
    )
    hours = calculate_cycle_hours(cycle)

    return {
        "cycle_name": cycle.name.name,
        "funding": cycle.funding_type.name if cycle.funding_type else "",
        "start": cycle.start_date.strftime("%d.%m.%Y"),
        "end": cycle.end_date.strftime("%d.%m.%Y"),
        "base": cycle.base.name,
        "compiled_by": cycle.compiled_by.short_name,
        "lessons": [
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
        ],
        "hours_summary": hours.by_type,
        "total_hours": hours.total,
    }


def schedule_filename(cycle) -> str:
    return f"Расписание_{cycle.name.name}_{cycle.start_date:%Y-%m-%d}.docx"


def export_schedule(cycle) -> HttpResponse:
    """Готовый HTTP-ответ с расписанием цикла."""
    tpl = get_active_template("schedule")
    context = build_schedule_context(cycle)
    data = render_docx(tpl.file.path, context)
    return docx_response(data, schedule_filename(cycle))

