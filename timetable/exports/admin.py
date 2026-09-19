from django import forms
from django.contrib import admin
from django.utils.html import format_html

from timetable.exports.kinds import all_specs
from timetable.exports.models import DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "kind", "uploaded_at", "uploaded_by",
        "download_link", "comment",
    )
    list_filter = ("kind",)
    search_fields = ("comment",)
    readonly_fields = ("uploaded_at", "uploaded_by", "download_link")
    fields = (
        "kind", "file", "comment",
        "download_link", "uploaded_by", "uploaded_at",
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # SlugField → select с актуальными видами из реестра.
        if db_field.name == "kind":
            kwargs["widget"] = forms.Select(
                choices=[(s.code, s.name) for s in all_specs()],
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Скачать")
    def download_link(self, obj):
        if not obj.pk or not obj.file:
            return "—"
        return format_html(
            '<a href="{}" target="_blank">Скачать</a>', obj.file.url,
        )

