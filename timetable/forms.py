from django import forms

from .models import Lesson
from timetable.xlsx_utils import validate_xlsx_extension


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


class CycleImportForm(forms.Form):
    """Загрузка XLSX для импорта цикла."""

    file = forms.FileField(
        label="XLSX-файл",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        validators=[validate_xlsx_extension],
    )
