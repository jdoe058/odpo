from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from timetable.models import Cycle
from timetable.exports.schedule import export_schedule
from timetable.exports.teacher_load import export_teacher_load


@login_required
def schedule_export_view(request, object_id):
    cycle = get_object_or_404(
        Cycle.objects.select_related(
            "name", "funding_type", "base", "compiled_by",
        ),
        pk=object_id,
    )
    return export_schedule(cycle)


@login_required
def teacher_load_export_view(request, object_id):
    cycle = get_object_or_404(
        Cycle.objects.select_related("name", "base", "compiled_by"),
        pk=object_id,
    )
    return export_teacher_load(cycle)


