from timetable.exports.kinds import ExporterSpec, register
from timetable.services.cycle_hours import calculate_cycle_hours


def build_context(cycle) -> dict:
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
                "date": l.date.strftime("%d.%m.%Y"),
                "time": f"{l.time_start:%H:%M}-{l.time_end:%H:%M}",
                "type": l.lesson_type.name,
                "hours": l.hours,
                "topic": l.topic,
                "teacher": l.employee.short_name,
            }
            for l in lessons
        ],
        "hours_summary": hours.by_type,
        "total_hours": hours.total,
    }


def build_filename(cycle) -> str:
    return f"schedule_{cycle.name.name}_{cycle.start_date:%Y-%m-%d}.docx"


register(ExporterSpec(
    code="schedule",
    name="Расписание",
    sort_order=10,
    build_context=build_context,
    build_filename=build_filename,
))