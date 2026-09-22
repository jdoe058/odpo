from django import forms
from .models import Lesson


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
