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

@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "approved_by")
    list_filter = ("name",)
    search_fields = ("name__name", "approved_by__short_name")
    date_hierarchy = "start_date"
    autocomplete_fields = ("name", "approved_by")

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("date", "time_start", "time_end", "hours",
                    "lesson_type", "topic", "employee", "cycle")
    list_filter = ("cycle", "lesson_type", "employee")
    search_fields = ("topic", "employee__short_name")
    date_hierarchy = "date"
    autocomplete_fields = ("cycle", "lesson_type", "employee")    