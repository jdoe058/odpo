from io import BytesIO
from urllib.parse import quote

from django.http import HttpResponse, Http404
from docxtpl import DocxTemplate

from timetable.models import DocumentTemplate


DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document"
)


def get_active_template(kind_code: str) -> DocumentTemplate:
    """
    Активный шаблон указанного типа. Бросает Http404, если не загружен.
    """
    tpl = (
        DocumentTemplate.objects
        .filter(kind__code=kind_code, is_active=True)
        .first()
    )
    if tpl is None:
        raise Http404(
            f"Активный шаблон «{kind_code}» не загружен. "
            "Загрузите его в разделе «Шаблоны документов»."
        )
    return tpl


def render_docx(template_path: str, context: dict) -> bytes:
    """Рендерит .docx по шаблону и возвращает байты."""
    tpl = DocxTemplate(template_path)
    tpl.render(context)

    buf = BytesIO()
    tpl.save(buf)
    return buf.getvalue()


def docx_response(data: bytes, filename: str) -> HttpResponse:
    """Оборачивает байты .docx в HttpResponse с правильными заголовками."""
    response = HttpResponse(data, content_type=DOCX_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quote(filename)}"
    )
    return response

