from timetable.exports.kinds import ExporterSpec, register
from timetable.services.timesheet import calculate_timesheet


def build_own_context(cycle) -> dict:
    return {
        "months": calculate_timesheet(cycle),
    }


def build_filename(cycle) -> str:
    return (
        f"timesheet_{cycle.name.name}_"
        f"{cycle.start_date:%Y-%m-%d}.docx"
    )


register(ExporterSpec(
    code="timesheet",
    name="Табель",
    sort_order=30,
    build_own_context=build_own_context,
    build_filename=build_filename,
))