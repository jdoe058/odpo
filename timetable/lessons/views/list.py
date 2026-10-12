"""Список занятий."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from timetable.exports.kinds import all_specs
from timetable.schedule_filter import (
    ScheduleFilterMixin, build_common_context,
)
from timetable.services.lesson_gaps import find_lesson_gaps

from ._helpers import build_lessons


class LessonList(LoginRequiredMixin, ScheduleFilterMixin, TemplateView):
    """Список занятий с фильтром расписания."""

    template_name = "timetable/lessons/lesson_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(build_common_context(self))

        lessons = build_lessons(self.filter_data)

        ctx.update({
            "lessons": lessons,
            "lesson_gaps": find_lesson_gaps(lessons),
            "export_kinds": all_specs(),
        })
        return ctx