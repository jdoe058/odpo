"""Миксин фильтра расписания для CBV."""
from functools import cached_property

from django.views import View

from .form import ScheduleFilterForm


class ScheduleFilterMixin(View):
    """
    Даёт CBV доступ к разобранному фильтру расписания.

    self.filter_form — ScheduleFilterForm, связанная с request.GET.
    self.filter_data — cleaned_data формы (словарь).
    """

    @cached_property
    def filter_form(self):
        form = ScheduleFilterForm(self.request.GET)
        form.is_valid()
        return form

    @cached_property
    def filter_data(self):
        return self.filter_form.cleaned_data