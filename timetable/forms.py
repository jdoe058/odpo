from django import forms


class ScheduleImportForm(forms.Form):
    file = forms.FileField(
        label="XLSX-файл",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )