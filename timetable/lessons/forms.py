"""Формы для CRUD занятий."""
from django import forms
from django_select2.forms import ModelSelect2Widget

from timetable.models import Base, Cycle, Employee, Lesson, LessonType


_SELECT2_ATTRS = {
    "data-placeholder": "Начните вводить…",
    "data-minimum-input-length": 0,
    "style": "width: 100%",
}


class LessonForm(forms.ModelForm):
    """Создание и редактирование занятия."""

    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )
    time_start = forms.TimeField(
        label="Начало",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    hours = forms.IntegerField(
        label="Часы",
        min_value=1,
        widget=forms.NumberInput(attrs={"min": 1}),
    )
    break_after_minutes = forms.IntegerField(
        label="Перемена после урока, мин",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"min": 0}),
        help_text="Оставьте пусто, если стандартная перемена (10 минут).",
    )

    class Meta:
        model = Lesson
        fields = [
            "cycle",
            "date",
            "time_start",
            "hours",
            "lesson_type",
            "topic",
            "employee",
            "break_after_minutes",
            "base",
        ]
        widgets = {
            "cycle": ModelSelect2Widget(
                model=Cycle,
                search_fields=["name__name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
            "lesson_type": ModelSelect2Widget(
                model=LessonType,
                search_fields=["name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
            "employee": ModelSelect2Widget(
                model=Employee,
                search_fields=["short_name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
            "base": ModelSelect2Widget(
                model=Base,
                search_fields=["name__icontains"],
                attrs=_SELECT2_ATTRS,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        default_break = Lesson._meta.get_field("break_after_minutes").default

        if self.instance.pk:
            # Редактирование: если у объекта дефолт — показываем пустое поле.
            if self.instance.break_after_minutes == default_break:
                self.initial["break_after_minutes"] = ""
        else:
            # Создание: всегда пустое поле, дефолт подставит clean_.
            self.initial["break_after_minutes"] = ""

    def clean_break_after_minutes(self):
        value = self.cleaned_data.get("break_after_minutes")
        if value is None:
            return Lesson._meta.get_field("break_after_minutes").default
        return value