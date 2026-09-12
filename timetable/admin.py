from django.contrib import admin
from .models import Employee, Position, Base, LessonType, FundingType, CycleName, Cycle
    
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