from django import forms

from timetable.xlsx_utils import validate_xlsx_extension


class CycleImportForm(forms.Form):
    """Загрузка XLSX для импорта цикла."""

    file = forms.FileField(
        label="XLSX-файл",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        validators=[validate_xlsx_extension],
    )
