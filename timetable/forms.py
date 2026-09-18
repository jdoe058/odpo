from django import forms
from .models import Lesson


class ScheduleImportForm(forms.Form):
    file = forms.FileField(
        label="XLSX-файл",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

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
            "time_end",
            "lesson_type",
            "topic",
            "employee",
        ]
        widgets = {
            "time_start": forms.TimeInput(attrs={"type": "time"}),
            "time_end": forms.TimeInput(attrs={"type": "time"}),
        }
