"""Вспомогательные функции для view занятий."""
from timetable.models import Lesson
from timetable.schedule_filter import filter_lessons


def build_lessons(data: dict):
    """
    Строит queryset занятий по разобранным данным фильтра расписания.

    Логика: цикл + база + преподаватель, как на странице занятий.
    """
    cycle = data.get("cycle")
    base = data.get("base")

    if cycle is not None:
        qs = (
            Lesson.objects
            .filter(
                cycle=cycle,
                date__gte=data["resolved_start"],
                date__lte=data["resolved_end"],
            )
            .select_related("lesson_type", "employee", "cycle", "cycle__name")
            .order_by("date", "time_start")
        )
        return filter_lessons(qs, data)

    if base is not None or data["employee_query"]:
        qs = (
            Lesson.objects
            .filter(
                date__gte=data["resolved_start"],
                date__lte=data["resolved_end"],
            )
            .select_related(
                "lesson_type", "employee", "cycle", "cycle__name", "base",
            )
            .order_by("date", "time_start")
        )
        return filter_lessons(qs, data)

    return Lesson.objects.none()