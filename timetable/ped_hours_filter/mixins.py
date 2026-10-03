"""Миксин фильтра отчёта «Педагогические часы» для CBV."""
from functools import cached_property

from django.views import View

from .form import PedHoursFilterForm


class PedHoursFilterMixin(View):
    """
    Даёт CBV доступ к разобранному фильтру отчёта.

    self.filter_form — PedHoursFilterForm, связанная с request.GET.
    self.filter_data — cleaned_data формы, содержит числовые year и month.
    """

    @cached_property
    def filter_form(self):
        form = PedHoursFilterForm(self.request.GET)
        form.is_valid()
        return form

    @cached_property
    def filter_data(self):
        return self.filter_form.cleaned_data