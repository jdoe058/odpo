from pathlib import Path

from django.core.files.base import ContentFile
from django.http import Http404

from timetable.exports.models import DocumentTemplate

SEED_TEMPLATES_DIR = Path(__file__).resolve().parent / "seed_templates"

def get_active_template(kind_code: str) -> DocumentTemplate:
    tpl = (
        DocumentTemplate.objects
        .filter(kind=kind_code, is_active=True)
        .first()
    )
    if tpl is None:
        raise Http404(
            f"Активный шаблон «{kind_code}» не загружен. "
            "Загрузите его в разделе «Шаблоны документов»."
        )
    return tpl


def template_status() -> list[dict]:
    """
    Для дашборда/админки: по каждому зарегистрированному виду —
    активный шаблон или None.
    """
    from timetable.exports.kinds import all_specs
    active = {
        t.kind: t
        for t in DocumentTemplate.objects.filter(is_active=True)
    }
    return [
        {"spec": spec, "template": active.get(spec.code)}
        for spec in all_specs()
    ]

def seed_templates() -> list[tuple[str, bool]]:
    """
    Копирует эталонные .docx из seed_templates/ в медиахранилище
    и создаёт DocumentTemplate(is_active=True), если активного
    шаблона для этого вида ещё нет.

    Возвращает список (kind_code, created). Виды, для которых
    в seed_templates/ нет файла, в результат не попадают.
    """
    from timetable.exports.kinds import codes  # локально: реестр наполняется в apps.ready()

    result: list[tuple[str, bool]] = []
    for code in codes():
        source = SEED_TEMPLATES_DIR / f"{code}.docx"
        if not source.exists():
            continue
        if DocumentTemplate.objects.filter(kind=code, is_active=True).exists():
            result.append((code, False))
            continue
        tpl = DocumentTemplate(
            kind=code,
            is_active=True,
            comment="Эталонный шаблон из репозитория",
            file=ContentFile(source.read_bytes(), name=f"{code}.docx"),
        )
        tpl.save()
        result.append((code, True))
    return result

