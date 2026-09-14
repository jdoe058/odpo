from django.http import Http404

from timetable.exports.models import DocumentTemplate


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

