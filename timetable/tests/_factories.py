"""
Хелперы для тестов. Не тесты — общие фабрики.

Пока здесь только генерация минимального .docx. По мере роста набора
тестов сюда переедут make_cycle, make_employee, make_approver и т.п.
"""
from io import BytesIO

from docx import Document


def make_docx_bytes(placeholders: list[str] | None = None) -> bytes:
    """
    Минимальный валидный .docx. Если переданы `placeholders`, каждый
    становится отдельным абзацем вида `{{ name }}` — пригодно для
    проверки рендера через docxtpl.

    Не читает диск и не требует MEDIA_ROOT — возвращает bytes.
    """
    doc = Document()
    for ph in placeholders or []:
        doc.add_paragraph("{{ " + ph + " }}")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
