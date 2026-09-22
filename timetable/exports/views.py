from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from timetable.models import Cycle
from timetable.exports.base import render_docx, docx_response
from timetable.exports.kinds import get as get_spec
from timetable.exports.library import get_latest_template
from timetable.exports.cycle_xlsx_export import cycle_to_xlsx_bytes

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

@login_required
def cycle_xlsx_export_view(request, cycle_id):
    cycle = get_object_or_404(
        Cycle.objects.select_related("name", "base", "funding_type", "compiled_by"),
        pk=cycle_id,
    )
    content = cycle_to_xlsx_bytes(cycle)
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )

    def _safe(s: str) -> str:
        return "".join(c for c in s if c not in '/\\:"<>|?*').strip()

    filename = (
        f"{cycle.start_date:%Y-%m-%d}_"
        f"{_safe(cycle.base.name)}_"
        f"{_safe(cycle.name.name)}.xlsx"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="cycle.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return response