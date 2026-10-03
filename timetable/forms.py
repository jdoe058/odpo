from django import forms
from .models import Lesson
from .services.ped_hours import MONTH_NAMES_RU, available_years


class LessonForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )

    class Meta:
        model = Lesson
        fields = [
            "date",
            "hours",
            "time_start",
            "lesson_type",
            "topic",
            "employee",
        ]
        widgets = {
            "time_start": forms.TimeInput(attrs={"type": "time"}),
        }

class PedHoursFilterForm(forms.Form):
    """Фильтр отчёта «Педагогические часы»."""

    year = forms.ChoiceField(label="Год")
    month = forms.ChoiceField(label="Месяц")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        year_field: forms.ChoiceField = self.fields["year"]  # type: ignore[assignment]
        year_field.choices = [(y, y) for y in available_years()]

        month_field: forms.ChoiceField = self.fields["month"]  # type: ignore[assignment]
        month_field.choices = [
            (i + 1, name) for i, name in enumerate(MONTH_NAMES_RU[1:])
        ]
        