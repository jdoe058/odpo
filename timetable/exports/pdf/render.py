"""Рендер HTML в PDF через WeasyPrint."""
from pathlib import Path
from urllib.parse import quote

from django.http import HttpResponse
from weasyprint import CSS, HTML


PDF_CONTENT_TYPE = "application/pdf"

CSS_DIR = Path(__file__).resolve().parent / "css"


def render_pdf(html: str, *css_names: str) -> bytes:
    """
    HTML-строка + имена CSS-файлов (без расширения или с ним)
    → байты PDF.
    """
    css_text = "\n".join(_read_css(name) for name in css_names)
    stylesheets = [CSS(string=css_text)] if css_text else []

    result = HTML(string=html).write_pdf(stylesheets=stylesheets)
    if result is None:
        raise RuntimeError("WeasyPrint вернул пустой PDF")
    return result


def pdf_response(data: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(data, content_type=PDF_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f'attachment; filename="document.pdf"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return response


def _read_css(name: str) -> str:
    if not name.endswith(".css"):
        name = f"{name}.css"
    path = CSS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"PDF CSS not found: {path}")
    return path.read_text(encoding="utf-8")