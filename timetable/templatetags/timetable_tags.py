from django import template

from timetable.references.registry import all_specs

register = template.Library()


@register.simple_tag
def get_reference_specs():
    return all_specs()