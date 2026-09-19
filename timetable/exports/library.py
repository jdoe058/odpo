from pathlib import Path

from django.core.files.base import ContentFile
from django.http import Http404

from timetable.exports.models import DocumentTemplate

SEED_TEMPLATES_DIR = Path(__file__).resolve().parent / "seed_templates"


def get_latest_template(kind_code: str) -> DocumentTemplate:
    """
    Рабочий шаблон для kind — последний загруженный.

    История версий сохраняется: старые записи остаются в БД, их можно
    скачать или вернуть. Для экспорта всегда берётся самая свежая.
    """
    tpl = (
        DocumentTemplate.objects
        .filter(kind=kind_code)
        .order_by("-uploaded_at")
        .first()
    )
    if tpl is None:
        raise Http404(
            f"Шаблон «{kind_code}» не загружен. "
            "Загрузите его в разделе «Шаблоны документов»."
        )
    return tpl


def template_status() -> list[dict]:
    """
    По каждому зарегистрированному виду — последний загруженный
    шаблон или None.
    """
    from timetable.exports.kinds import all_specs

    latest: dict[str, DocumentTemplate] = {}
    for tpl in DocumentTemplate.objects.order_by("kind", "-uploaded_at"):
        latest.setdefault(tpl.kind, tpl)

    return [
        {"spec": spec, "template": latest.get(spec.code)}
        for spec in all_specs()
    ]


def seed_templates() -> list[tuple[str, bool]]:
    """
    Копирует эталонные .docx из seed_templates/ в медиахранилище
    и создаёт DocumentTemplate для тех видов, у которых в БД ещё
    нет ни одной записи.

    Возвращает список (kind_code, created). Виды, для которых
    в seed_templates/ нет файла, в результат не попадают.
    """
    from timetable.exports.kinds import codes  # локально: реестр наполняется в apps.ready()

    result: list[tuple[str, bool]] = []
    for code in codes():
        source = SEED_TEMPLATES_DIR / f"{code}.docx"
        if not source.exists():
            continue
        if DocumentTemplate.objects.filter(kind=code).exists():
            result.append((code, False))
            continue
        tpl = DocumentTemplate(
            kind=code,
            comment="Эталонный шаблон из репозитория",
            file=ContentFile(source.read_bytes(), name=f"{code}.docx"),
        )
        tpl.save()
        result.append((code, True))
    return result