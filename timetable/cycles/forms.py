"""Формы для CRUD циклов."""
from django import forms
from django_select2.forms import ModelSelect2Widget

from timetable.models import Base, Cycle, CycleName, Employee


_SELECT2_ATTRS = {
    "data-placeholder": "Начните вводить…",
    "data-minimum-input-length": 0,
    "style": "width: 100%",
}


class CycleForm(forms.ModelForm):
    """Создание и редактирование цикла."""

    start_date = forms.DateField(
        label="Дата начала",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )
    end_date = forms.DateField(
        label="Дата окончания",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )

    class Meta:
        model = Cycle
        fields = [
            "name", "kind", "funding_type", "base",
            "start_date", "end_date", "compiled_by",
        ]
        widgets = {
            "name": ModelSelect2Widget(
                model=CycleName,
                search_fields=["name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
            "base": ModelSelect2Widget(
                model=Base,
                search_fields=["name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
            "compiled_by": ModelSelect2Widget(
                model=Employee,
                search_fields=["short_name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Финансирование — простой select, растянуть на ширину.
        self.fields["funding_type"].widget.attrs["style"] = "width: 100%"

class CycleFilterForm(forms.Form):
    """Фильтр списка циклов: поиск по названию и по базе."""

    q = forms.CharField(
        required=False,
        label="Поиск",
        widget=forms.TextInput(attrs={
            "type": "search",
            "placeholder": "Часть названия",
            "style": "min-width: 260px;",
        }),
    )
    base = forms.ModelChoiceField(
        required=False,
        label="База",
        queryset=Base.objects.all(),
        empty_label="— все —",
    )