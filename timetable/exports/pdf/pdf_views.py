"""PDF-выгрузки циклов. Пока поддерживается только расписание."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from timetable.models import Cycle
from timetable.exports.kinds import get as get_spec
from timetable.exports.pdf.render import pdf_response, render_pdf


# Виды, для которых уже есть HTML-шаблон и CSS.
# Расширяется по мере готовности: в коммите 3 добавим teacher_load,
# в коммите 4 — timesheet.
PDF_KINDS = frozenset({"schedule", "teacher_load"})


def build_pdf_for_cycle(cycle, kind: str) -> bytes:
    """Собрать PDF без обращения к HTTP. Удобно тестировать и вызывать из shell."""
    spec = get_spec(kind)
    context = spec.build_context(cycle)
    html = render_to_string(
        f"timetable/exports/pdf/{kind}.html", context,
    )
    return render_pdf(html, "base", kind)


@login_required
def export_pdf_view(request, cycle_id: int, kind: str):
    if kind not in PDF_KINDS:
        raise Http404(f"PDF-выгрузка «{kind}» недоступна")

    cycle = get_object_or_404(
        Cycle.objects.select_related(
            "name", "funding_type", "base", "compiled_by",
        ),
        pk=cycle_id,
    )

    data = build_pdf_for_cycle(cycle, kind)
    filename = get_spec(kind).build_filename(cycle).replace(".docx", ".pdf")
    return pdf_response(data, filename)