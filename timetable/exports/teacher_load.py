from django.http import HttpResponse

from timetable.exports.base import (
    get_active_template, render_docx, docx_response,
)
from timetable.services.teacher_load import calculate_teacher_load


def build_teacher_load_context(cycle) -> dict:
    load = calculate_teacher_load(cycle)
    return {
        "cycle_name": cycle.name.name,
        "start": cycle.start_date.strftime("%d.%m.%Y"),
        "end": cycle.end_date.strftime("%d.%m.%Y"),
        "base": cycle.base.name,
        "rows": [
            {
                "n": r.n,
                "teacher": r.teacher,
                "lecture": r.lecture,
                "seminar": r.seminar,
                "practice": r.practice,
                "total": r.total,
            }
            for r in load.rows
        ],
        "total_lecture": load.total_lecture,
        "total_seminar": load.total_seminar,
        "total_practice": load.total_practice,
        "grand_total": load.grand_total,
        "signer": cycle.compiled_by.short_name,
    }


def teacher_load_filename(cycle) -> str:
    return (
        f"Распределение часов_{cycle.name.name}_"
        f"{cycle.start_date:%Y-%m-%d}.docx"
    )


def export_teacher_load(cycle) -> HttpResponse:
    tpl = get_active_template("teacher_load")
    context = build_teacher_load_context(cycle)
    data = render_docx(tpl.file.path, context)
    return docx_response(data, teacher_load_filename(cycle))