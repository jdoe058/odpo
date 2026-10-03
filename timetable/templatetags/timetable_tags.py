from django import template

from timetable.references.registry import all_specs

register = template.Library()


@register.simple_tag
def get_reference_specs():
    return all_specs()

@register.filter
def get_attr(obj, name: str):
    """Значение атрибута для отображения в шаблоне."""
    value = getattr(obj, name, None)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    return value