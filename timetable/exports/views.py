from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404

from timetable.models import Cycle
from timetable.exports.base import render_docx, docx_response
from timetable.exports.kinds import get as get_spec
from timetable.exports.library import get_latest_template
from .cycle_csv import cycle_to_csv_bytes


@login_required
def export_view(request, cycle_id: int, kind: str):
    """
    Универсальная выгрузка: вид определяется слагом `kind`
    по реестру timetable.exports.kinds.
    """
    cycle = get_object_or_404(
        Cycle.objects.select_related(
            "name", "funding_type", "base", "compiled_by",
        ),
        pk=cycle_id,
    )

    try:
        spec = get_spec(kind)
    except KeyError:
        raise Http404(f"Неизвестный тип выгрузки: {kind!r}")

    tpl = get_latest_template(kind)           # Http404, если шаблон не загружен
    data = render_docx(tpl.file.path, spec.build_context(cycle))
    return docx_response(data, spec.build_filename(cycle))

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from timetable.models import Cycle
from .cycle_csv import cycle_to_csv_bytes

@login_required
def cycle_export_csv_view(request, cycle_id):
    cycle = get_object_or_404(
        Cycle.objects.select_related("name", "base", "funding_type", "compiled_by"),
        pk=cycle_id,
    )
    content = cycle_to_csv_bytes(cycle)
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    filename = f"{cycle.name.name}_{cycle.start_date:%Y-%m-%d}.csv"
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}'
    )
    return response

@login_required
def cycle_export_csv_view(request, cycle_id):
    cycle = get_object_or_404(
        Cycle.objects.select_related("name", "base", "funding_type", "compiled_by"),
        pk=cycle_id,
    )
    content = cycle_to_csv_bytes(cycle)
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    filename = f"{cycle.name.name}_{cycle.start_date:%Y-%m-%d}.csv"
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}'
    )
    return response