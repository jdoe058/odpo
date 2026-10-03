from functools import lru_cache

from django import forms
from django.forms import modelform_factory
from django_select2.forms import ModelSelect2Widget

from .registry import get_spec


# Общие атрибуты для всех FK-виджетов.
# data-minimum-input-length=0 — разрешает показывать первые элементы
# списка ещё до начала ввода.
_SELECT2_ATTRS = {
    "data-placeholder": "Начните вводить…",
    "data-minimum-input-length": 0,
    "style": "width: 100%",
}


@lru_cache(maxsize=None)
def get_form_class(slug: str):
    """
    ModelForm-класс для справочника по slug.

    Поля берутся из spec.columns. Для FK-колонок (`kind="fk_name"`)
    подставляется Select2-виджет с поиском по `fk_attr`
    (по умолчанию — `name`).
    """
    spec = get_spec(slug)
    if spec is None:
        raise ValueError(f"Unknown reference slug: {slug!r}")

    widgets = {}
    for col in spec.columns:
        if col.kind != "fk_name":
            continue
        field = spec.model._meta.get_field(col.name)
        widgets[col.name] = ModelSelect2Widget(
            model=field.related_model,
            search_fields=[f"{col.fk_attr}__icontains"],
            attrs=_SELECT2_ATTRS,
        )

    return modelform_factory(
        spec.model,
        fields=[c.name for c in spec.columns],
        widgets=widgets,
    )

class ReferenceSearchForm(forms.Form):
    """Поле поиска в списке справочника. GET, все поля необязательные."""

    q = forms.CharField(
        required=False,
        label="Поиск",
        widget=forms.TextInput(attrs={
            "type": "search",
            "placeholder": "Часть названия",
            "style": "min-width: 260px;",
        }),
    )