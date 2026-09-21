from django.urls import path, reverse
from django.contrib import admin
from django.utils.html import format_html_join
from .views import schedule_import_view
from .models import (
    Employee, Position, Base, LessonType, FundingType, CycleName, Cycle, Lesson, 
)

from timetable.exports.kinds import all_specs
from timetable.exports.views import export_view as cycle_export_view

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "max_hours_per_day",
        "max_hours_per_week",
        "max_hours_per_year",
        "can_sign", "can_approve",
        "sort_order",
    )
    list_editable = (
        "max_hours_per_day",
        "max_hours_per_week",
        "max_hours_per_year",
        "can_sign", "can_approve",
        "sort_order",
    )
    search_fields = ("name",)
    ordering = ("sort_order", "name")

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "short_name", "position", "base",
        "max_hours_per_day", "max_hours_per_week", "max_hours_per_year",
    )
    list_filter = ("position", "base",)
    search_fields = ("short_name",)
    ordering = ("short_name",)
    autocomplete_fields = ("position", "base")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "position" not in initial:
            default_position = Position.objects.filter(
                name="Преподаватель-совместитель"
            ).first()
            if default_position is not None:
                initial["position"] = default_position.pk
        return initial

    @admin.display(description="Макс. часов/день")
    def max_hours_per_day(self, obj):
        return obj.max_hours_per_day

    @admin.display(description="Подписывает", boolean=True)
    def can_sign(self, obj):
        return obj.can_sign

    @admin.display(description="Утверждает", boolean=True)
    def can_approve(self, obj):
        return obj.can_approve

@admin.register(Base)
class BaseAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(LessonType)
class LessonTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "sort_order", "counts_in_hours")
    list_editable = ("name", "category", "sort_order", "counts_in_hours")
    list_filter = ("category", "counts_in_hours")
    search_fields = ("code", "name")
    ordering = ("sort_order",)

@admin.register(FundingType)
class FundingTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(CycleName)
class CycleNameAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("date", "time_start", "time_end", "hours",
                    "lesson_type", "topic", "employee", "cycle")
    list_filter = ("cycle", "lesson_type", "employee")
    search_fields = ("topic", "employee__short_name")
    date_hierarchy = "date"
    autocomplete_fields = ("cycle", "lesson_type", "employee")

@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = (
        "start_date", "base", "name",
    )
    list_filter = ("name", "base")
    search_fields = ("name__name", "base__name", "compiled_by__short_name")
    date_hierarchy = "start_date"
    autocomplete_fields = ("name", "compiled_by", "base")

    change_list_template = "admin/timetable/cycle/change_list.html"



    readonly_fields = ("export_links",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import/",
                self.admin_site.admin_view(
                    lambda request: schedule_import_view(request, self.admin_site)
                ),
                name="timetable_cycle_import",
            ),
            path(
                "<path:cycle_id>/export/<slug:kind>/",
                self.admin_site.admin_view(cycle_export_view),
                name="timetable_cycle_export",
            ),
        ]
        return custom + urls

    @admin.display(description="Выгрузки")
    def export_links(self, obj):
        if obj is None or not obj.pk:
            return "Сохраните цикл, чтобы выгрузить документы."
        return format_html_join(
            " ",
            '<a class="button" href="{}">{}</a>',
            [
                (
                    reverse(
                        "admin:timetable_cycle_export",
                        args=[obj.pk, spec.code],
                    ),
                    spec.name,
                )
                for spec in all_specs()
            ],
        )
