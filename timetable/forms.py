from django import forms
from django.db.models import Q

from timetable.services.periods import resolve_period
from timetable.xlsx_utils import validate_xlsx_extension
from .models import Base, Cycle, Lesson, normalize_short_name
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


class CycleImportForm(forms.Form):
    """Загрузка XLSX для импорта цикла."""

    file = forms.FileField(
        label="XLSX-файл",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        validators=[validate_xlsx_extension],
    )

class _LenientDateField(forms.DateField):
    """DateField, который не падает на мусор — просто возвращает None."""

    def to_python(self, value):
        if not value:
            return None
        try:
            return super().to_python(value)
        except forms.ValidationError:
            return None


class _LenientModelChoiceField(forms.ModelChoiceField):
    """ModelChoiceField, который не падает на несуществующий pk."""

    def to_python(self, value):
        if not value:
            return None
        try:
            return super().to_python(value)
        except forms.ValidationError:
            return None


class ScheduleFilterForm(forms.Form):
    """
    Фильтры на странице расписания.

    Все поля необязательные и «снисходительные»: любое невалидное значение
    (плохая дата, несуществующий pk) трактуется как «не выбрано».
    Форма всегда валидна.
    """

    period = forms.ChoiceField(
        required=False,
        choices=[
            ("week", "Неделя"),
            ("month", "Месяц"),
            ("year", "Учебный год"),
            ("custom", "Произвольный"),
        ],
    )
    anchor = _LenientDateField(required=False)
    start = _LenientDateField(required=False)
    end = _LenientDateField(required=False)
    base = _LenientModelChoiceField(
        required=False,
        queryset=Base.objects.all(),
        empty_label="— все базы —",
    )
    cycle = _LenientModelChoiceField(
        required=False,
        queryset=Cycle.objects.select_related("name", "base"),
        empty_label="— все —",
    )
    employee = forms.CharField(
        required=False,
        label="Преподаватели",
        widget=forms.TextInput(attrs={
            "placeholder": "МАРКОВ, СОКОЛОВА",
            "id": "id_employee",
        }),
    )

    def clean(self):
        cleaned = super().clean()

        # --- период ---
        period = cleaned.get("period") or "week"
        if period not in {"week", "month", "year", "custom"}:
            period = "week"

        cycle = cleaned.get("cycle")
        anchor = cleaned.get("anchor")
        if anchor is None and cycle is not None:
            anchor = cycle.start_date

        start = cleaned.get("start")
        end = cleaned.get("end")

        try:
            if period == "custom" and start and end:
                start, end = resolve_period("custom", start=start, end=end)
            else:
                if period == "custom":
                    period = "week"
                start, end = resolve_period(period, anchor)
        except (ValueError, TypeError):
            period = "week"
            start, end = resolve_period(period)

        cleaned["period"] = period
        cleaned["resolved_start"] = start
        cleaned["resolved_end"] = end

        # --- преподаватели ---
        employee_query = (cleaned.get("employee") or "").strip()
        employee_q = Q()
        if employee_query:
            for part in employee_query.split(","):
                part = part.strip()
                if not part:
                    continue
                normalized = normalize_short_name(part)
                if normalized:
                    employee_q |= Q(employee__short_name__contains=normalized)
        cleaned["employee_query"] = employee_query
        cleaned["employee_q"] = employee_q

        return cleaned