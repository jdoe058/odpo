"""Динамические ModelForm для справочников из реестра."""
from functools import lru_cache

from django.forms import modelform_factory

from .registry import get_spec


@lru_cache(maxsize=None)
def get_form_class(slug: str):
    """
    ModelForm-класс для справочника по slug.

    Поля берутся из spec.columns. Django сам подбирает виджеты:
    CharField → text, IntegerField → number, BooleanField → checkbox,
    ForeignKey → select. Тип поля в реестре (`kind`) влияет только
    на XLSX-импорт, для формы он не нужен.
    """
    spec = get_spec(slug)
    if spec is None:
        raise ValueError(f"Unknown reference slug: {slug!r}")
    return modelform_factory(spec.model, fields=[c.name for c in spec.columns])