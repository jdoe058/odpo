from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from timetable.models import Cycle
from timetable.exports.base import (
    get_active_template, render_docx, docx_response,
)
from timetable.exports.kinds import get as get_spec


def _export_cycle(request, cycle_id: int, kind_code: str):
    cycle = get_object_or_404(
        Cycle.objects.select_related(
            "name", "funding_type", "base", "compiled_by",
        ),
        pk=cycle_id,
    )
    spec = get_spec(kind_code)
    tpl = get_active_template(kind_code)
    data = render_docx(tpl.file.path, spec.build_context(cycle))
    return docx_response(data, spec.build_filename(cycle))


@login_required
def schedule_export_view(request, object_id):
    return _export_cycle(request, object_id, "schedule")


@login_required
def teacher_load_export_view(request, object_id):
    return _export_cycle(request, object_id, "teacher_load")

