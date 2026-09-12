from django.urls import path, reverse
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from .models import Employee, Position, Base, LessonType, FundingType, CycleName, Cycle, Lesson
from .services.cycle_hours import calculate_cycle_hours, prefetch_lessons_for_hours
from .services.employee_hours import calculate_employee_hours_all
from .views import employee_hours_report, schedule_import_view

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

    readonly_fields = ("hours_report_link",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/hours/",
                self.admin_site.admin_view(
                    lambda request, object_id: employee_hours_report(
                        request, object_id, self.admin_site,
                    )
                ),
                name="timetable_employee_hours",
            ),
        ]
        return custom + urls

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

    @admin.display(description="Часы по дням")
    def hours_report_link(self, obj):
        if obj is None or obj.pk is None:
            return "Сохраните сотрудника, чтобы увидеть отчёт."
        url = reverse("admin:timetable_employee_hours", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Открыть отчёт по часам</a>',
            url,
        )

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
        "name", "start_date", "end_date", "compiled_by",
        "total_hours", "breakdown_short",
    )
    list_filter = ("name",)
    search_fields = ("name__name", "compiled_by__short_name")
    date_hierarchy = "start_date"
    autocomplete_fields = ("name", "compiled_by")

    readonly_fields = ("hours_summary",)

    change_list_template = "admin/timetable/cycle/change_list.html"
    
    def get_queryset(self, request):
        return prefetch_lessons_for_hours(super().get_queryset(request))

    @admin.display(description="Всего часов")
    def total_hours(self, obj):
        return calculate_cycle_hours(obj).total

    @admin.display(description="По типам")
    def breakdown_short(self, obj):
        summary = calculate_cycle_hours(obj)
        if not summary.by_type:
            return "—"
        return ", ".join(f"{b.name}: {b.hours}" for b in summary.by_type)

    @admin.display(description="Часы по типам занятий")
    def hours_summary(self, obj):
        if obj is None or not obj.pk:
            return "—"
        summary = calculate_cycle_hours(obj)
        if not summary.by_type:
            return "Занятий с учётом часов пока нет."
        parts = ", ".join(f"{b.name}: {b.hours}" for b in summary.by_type)
        return f"{parts}. Итого: {summary.total} ч."

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
        ]
        return custom + urls