from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from timetable.references.inline import get_inline_value
from timetable.references.registry import menu_specs

register = template.Library()


@register.simple_tag
def get_reference_specs():
    return menu_specs()

@register.filter
def get_attr(obj, name: str):
    """Значение атрибута для отображения в шаблоне."""
    value = getattr(obj, name, None)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    return value


@register.inclusion_tag("timetable/references/_inline_cell.html")
def inline_cell(obj, col, spec):
    """Рендерит ячейку справочника как редактируемую через HTMX."""
    return {
        "obj": obj,
        "col": col,
        "spec": spec,
        "value": get_inline_value(obj, col),
    }

@register.simple_tag(takes_context=True)
def row_actions(
    context,
    *,
    edit="",
    add="",
    delete="",
    edit_next=None,
    add_next=None,
    delete_next=None,
    add_after=None,
    add_title="Добавить",
):
    """
    Кнопки действий в строке таблицы: изменить, добавить после, удалить.

    URL-ы передаются готовыми (через {% url ... as ... %}).
    Если *_next не задан — подставляется текущий URL (request.get_full_path).
    """
    request = context.get("request")
    current = request.get_full_path() if request else ""

    html = render_to_string(
        "timetable/_row_actions.html",
        {
            "edit_url": edit,
            "edit_next": current if edit_next is None else edit_next,
            "add_url": add,
            "add_after": add_after,
            "add_next": current if add_next is None else add_next,
            "add_title": add_title,
            "delete_url": delete,
            "delete_next": current if delete_next is None else delete_next,
        },
        request=request,
    )
    return mark_safe(html)