from timetable.exports.kinds import ExporterSpec, register
from timetable.services.teacher_load import calculate_teacher_load


def build_own_context(cycle) -> dict:
    load = calculate_teacher_load(cycle)
    return {
        "rows": [
            {
                "n": r.n, "teacher": r.teacher,
                "lecture": r.lecture, "seminar": r.seminar,
                "practice": r.practice, "total": r.total,
            }
            for r in load.rows
        ],
        "total_lecture": load.total_lecture,
        "total_seminar": load.total_seminar,
        "total_practice": load.total_practice,
        "grand_total": load.grand_total,
    }


def build_filename(cycle) -> str:
    return (
        f"teacher_load_{cycle.name.name}_"
        f"{cycle.start_date:%Y-%m-%d}.docx"
    )


register(ExporterSpec(
    code="teacher_load",
    name="Распределение часов преподавателей",
    sort_order=20,
    build_own_context=build_own_context,
    build_filename=build_filename,
))