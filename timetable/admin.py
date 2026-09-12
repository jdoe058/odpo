from django.contrib import admin
from .models import Employee, Position, Base, LessonType, FundingType, CycleName, Cycle, Lesson
    
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "name", "max_hours_per_day",
        "can_sign", "can_approve",
        "sort_order",
    )
    list_editable = ("max_hours_per_day", "can_sign", "can_approve", "sort_order")
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "short_name", "position",
        "max_hours_per_day", "can_sign", "can_approve",
    )
    list_filter = ("position",)
    search_fields = ("short_name",)
    ordering = ("short_name",)

    autocomplete_fields = ("position",)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial.setdefault(
            "position",
            Position.objects.filter(name="преподаватель-совместитель").first(),
        )
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
    list_display = ("code", "name", "sort_order", "counts_in_hours")
    list_editable = ("sort_order", "counts_in_hours")
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

from django.db.models import Sum, Q


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("date", "time_start", "time_end", "hours",
                    "lesson_type", "topic", "employee", "cycle")
    list_filter = ("cycle", "lesson_type", "employee")
    search_fields = ("topic", "employee__short_name")
    date_hierarchy = "date"
    autocomplete_fields = ("cycle", "lesson_type", "employee")

from django.utils.html import format_html, format_html_join

from .services.cycle_hours import calculate_cycle_hours, prefetch_lessons_for_hours


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "start_date", "end_date", "approved_by",
        "total_hours", "breakdown_short",
    )
    list_filter = ("name",)
    search_fields = ("name__name", "approved_by__short_name")
    date_hierarchy = "start_date"
    autocomplete_fields = ("name", "approved_by")

    readonly_fields = ("hours_breakdown",)

    def get_queryset(self, request):
        return prefetch_lessons_for_hours(super().get_queryset(request))

    # --- Колонки в списке ---

    @admin.display(description="Всего часов")
    def total_hours(self, obj):
        return calculate_cycle_hours(obj).total

    @admin.display(description="По типам")
    def breakdown_short(self, obj):
        summary = calculate_cycle_hours(obj)
        if not summary.by_type:
            return "—"
        return ", ".join(f"{b.code}: {b.hours}" for b in summary.by_type)

    # --- Таблица на странице редактирования ---

    @admin.display(description="Часы по типам занятий")
    def hours_breakdown(self, obj):
        if obj is None or not obj.pk:
            return "—"

        summary = calculate_cycle_hours(obj)
        if not summary.by_type:
            return "Занятий с учётом часов пока нет."

        rows = format_html_join(
            "",
            "<tr><td>{}</td><td style='text-align:right; padding-left:1em'>{}</td></tr>",
            ((b.name, b.hours) for b in summary.by_type),
        )
        return format_html(
            "<table style='border-collapse:collapse'>"
            "  <thead><tr>"
            "    <th style='text-align:left'>Тип занятия</th>"
            "    <th style='text-align:right'>Часов</th>"
            "  </tr></thead>"
            "  <tbody>{}</tbody>"
            "  <tfoot><tr>"
            "    <th style='text-align:left'>Итого</th>"
            "    <th style='text-align:right'>{}</th>"
            "  </tr></tfoot>"
            "</table>",
            rows,
            summary.total,
        )