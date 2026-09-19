"""
Формы модуля exports.

DocumentTemplateForm — для загрузки .docx-шаблонов через фронтовую
страницу. Поле kind рендерится как <select> с человекочитаемыми
названиями из реестра, а не как текстовый ввод слага.
"""
from django import forms

from timetable.exports.kinds import all_specs
from timetable.exports.models import DocumentTemplate


class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ["kind", "file", "comment"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": ".docx"}),
            "comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # kind — SlugField. Заменяем дефолтный CharField-widget
        # на Select с актуальными видами из реестра.
        self.fields["kind"].widget = forms.Select(
            choices=[(spec.code, spec.name) for spec in all_specs()],
        )