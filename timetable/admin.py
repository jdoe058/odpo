from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from django import forms
from .models import (
    Base, Cycle, CycleName, Discipline, EducationKind, Employee, FundingType,
    Lesson, LessonType, Position, WorkProgram,
)


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


class ChangeBaseForm(forms.Form):
    base = forms.ModelChoiceField(
        queryset=Base.objects.order_by("name"),
        label="Новая база",
        required=True,
    )


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
    actions = ["change_base", "clear_base"]

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

    @admin.action(description="Очистить базу у выбранных сотрудников")
    def clear_base(self, request, queryset):
        updated = queryset.update(base=None)
        self.message_user(
            request,
            f"База очищена у {updated} сотрудников.",
            messages.SUCCESS,
        )

    @admin.action(description="Сменить базу у выбранных сотрудников")
    def change_base(self, request, queryset):
        if "apply" in request.POST:
            form = ChangeBaseForm(request.POST)
            if form.is_valid():
                base = form.cleaned_data["base"]
                updated = queryset.update(base=base)
                self.message_user(
                    request,
                    f"База «{base}» установлена у {updated} сотрудников.",
                    messages.SUCCESS,
                )
                return None   # возврат в список
        else:
            form = ChangeBaseForm()

        return TemplateResponse(
            request,
            "admin/timetable/employee/change_base.html",
            {
                "title": "Смена базы",
                "queryset": queryset,
                "form": form,
                "opts": self.model._meta,
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            },
        )


@admin.register(Base)
class BaseAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(LessonType)
class LessonTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "sort_order")
    list_editable = ("name", "category", "sort_order")
    list_filter = ("category",)
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


class ChangeKindForm(forms.Form):
    """Форма для массовой смены вида у циклов."""

    kind = forms.ChoiceField(
        label="Новый вид",
        choices=EducationKind.choices,
    )


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = (
        "start_date", "base", "name", "stream", "kind",
    )
    list_filter = ("name", "base")
    search_fields = ("name__name", "base__name", "compiled_by__short_name")
    date_hierarchy = "start_date"
    autocomplete_fields = ("name", "compiled_by", "base")
    actions = ["change_kind"]

    @admin.action(description="Сменить вид у выбранных циклов")
    def change_kind(self, request, queryset):
        if "apply" in request.POST:
            form = ChangeKindForm(request.POST)
            if form.is_valid():
                kind = form.cleaned_data["kind"]
                updated = queryset.update(kind=kind)
                display = dict(EducationKind.choices)[kind]
                self.message_user(
                    request,
                    f"Вид «{display}» установлен у {updated} циклов.",
                    messages.SUCCESS,
                )
                return None
        else:
            form = ChangeKindForm()

        return TemplateResponse(
            request,
            "admin/timetable/cycle/change_kind.html",
            {
                "title": "Смена вида у циклов",
                "queryset": queryset,
                "form": form,
                "opts": self.model._meta,
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            },
        )


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("name_full", "name_short", "sort_order")
    list_editable = ("name_short", "sort_order")
    search_fields = ("name_full", "name_short")
    ordering = ("sort_order", "name_short")


@admin.register(WorkProgram)
class WorkProgramAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "kind", "discipline", "hours", "title")
    list_filter = ("academic_year", "kind", "discipline")
    search_fields = ("discipline__name_full", "discipline__name_short")
    autocomplete_fields = ("discipline",)
    ordering = ("-academic_year", "kind", "discipline__name_short")

    @admin.display(description="Название")
    def title(self, obj):
        return obj.title