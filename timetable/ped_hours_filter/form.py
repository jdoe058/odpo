"""Форма фильтра отчёта «Педагогические часы»."""
from datetime import date
from typing import cast

from django import forms

from timetable.services.ped_hours import MONTH_NAMES_RU, available_years


class PedHoursFilterForm(forms.Form):
    """Выбор месяца и года для отчёта. Всегда валидна, с дефолтами."""

    year = forms.ChoiceField(required=False, label="Год")
    month = forms.ChoiceField(required=False, label="Месяц")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        year_field = cast(forms.ChoiceField, self.fields["year"])
        year_field.choices = [(y, y) for y in available_years()]

        month_field = cast(forms.ChoiceField, self.fields["month"])
        month_field.choices = [
            (i + 1, name) for i, name in enumerate(MONTH_NAMES_RU[1:])
        ]

    def clean(self):
        cleaned = super().clean()
        today = date.today()

        try:
            year = int(cleaned.get("year") or today.year)
            month = int(cleaned.get("month") or today.month)
            if not (1 <= month <= 12):
                raise ValueError
            if not (2000 <= year <= 2100):
                raise ValueError
        except (ValueError, TypeError):
            year, month = today.year, today.month

        cleaned["year"] = year
        cleaned["month"] = month
        return cleaned