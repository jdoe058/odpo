"""Общие миксины для CBV справочников."""
from functools import cached_property

from django.http import Http404
from django.views import View

from timetable.references.registry import get_spec


def spec_or_404(slug: str):
    """Возвращает ReferenceSpec по slug или бросает Http404."""
    spec = get_spec(slug)
    if spec is None:
        raise Http404(f"Неизвестный справочник: {slug!r}")
    return spec


class ReferenceSpecMixin(View):
    """
    Даёт доступ к spec справочника через self.spec.

    Наследуемся от View, чтобы Pylance видел self.kwargs, self.request
    и прочие атрибуты CBV. Сам по себе миксин View не использует —
    только унаследованный интерфейс.
    """

    @cached_property
    def spec(self):
        return spec_or_404(self.kwargs["slug"])