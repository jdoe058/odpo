from io import BytesIO
from urllib.parse import quote

from django.http import HttpResponse
from docxtpl import DocxTemplate


DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document"
)


def render_docx(template_path: str, context: dict) -> bytes:
    tpl = DocxTemplate(template_path)
    tpl.render(context)
    buf = BytesIO()
    tpl.save(buf)
    return buf.getvalue()


def docx_response(data: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(data, content_type=DOCX_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quote(filename)}"
    )
    return response

