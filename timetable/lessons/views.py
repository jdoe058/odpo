"""CBV для CRUD занятий."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    CreateView, DeleteView, TemplateView, UpdateView,
)

from timetable.exports.kinds import all_specs
from timetable.models import Lesson
from timetable.schedule_filter import (
    ScheduleFilterMixin, build_common_context, filter_lessons,
)

from .forms import LessonForm


class LessonList(LoginRequiredMixin, ScheduleFilterMixin, TemplateView):
    """Список занятий с фильтром расписания."""

    template_name = "timetable/lessons/lesson_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(build_common_context(self))

        data = self.filter_data
        cycle = data.get("cycle")
        base = data.get("base")

        lessons = []
        if cycle is not None:
            qs = (
                Lesson.objects
                .filter(cycle=cycle)
                .select_related("lesson_type", "employee", "cycle", "cycle__name")
                .order_by("date", "time_start")
            )
            lessons = filter_lessons(qs, data)
        elif base is not None or data["employee_query"]:
            qs = (
                Lesson.objects
                .filter(date__gte=ctx["start"], date__lte=ctx["end"])
                .select_related(
                    "lesson_type", "employee", "cycle", "cycle__name", "base",
                )
                .order_by("date", "time_start")
            )
            lessons = filter_lessons(qs, data)

        ctx.update({
            "lessons": lessons,
            "export_kinds": all_specs(),
        })
        return ctx


class LessonCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Создание нового занятия."""

    model = Lesson
    form_class = LessonForm
    template_name = "timetable/lessons/lesson_form.html"
    success_message = "Занятие создано."

    def get_initial(self):
        initial = super().get_initial()

        after_pk = self.request.GET.get("after")
        cycle_pk = self.request.GET.get("cycle")

        if after_pk:
            prev = (
                Lesson.objects
                .select_related("cycle", "employee", "base")
                .filter(pk=after_pk)
                .first()
            )
            if prev is not None:
                initial.update({
                    "cycle": getattr(prev, "cycle_id", None),
                    "date": prev.date,
                    "time_start": prev.available_from,
                    "employee": getattr(prev, "employee_id", None),
                    "base": getattr(prev, "base_id", None),
                })
                return initial
        if cycle_pk:
            initial["cycle"] = cycle_pk
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_create"] = True
        ctx["next"] = self._next_url()
        return ctx

    def get_success_url(self):
        next_url = self._next_url()
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()},
        ):
            return next_url
        return reverse("timetable:lesson_list")

    def _next_url(self):
        return (
            self.request.GET.get("next")
            or self.request.POST.get("next")
            or ""
        )


class LessonEdit(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Редактирование занятия."""

    model = Lesson
    form_class = LessonForm
    template_name = "timetable/lessons/lesson_form.html"
    success_message = "Занятие сохранено."

    def get_queryset(self):
        return Lesson.objects.select_related("cycle", "cycle__name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_create"] = False
        ctx["next"] = self._next_url()
        return ctx

    def get_success_url(self):
        next_url = self._next_url()
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()},
        ):
            return next_url
        return reverse("timetable:lesson_list")

    def _next_url(self):
        return (
            self.request.GET.get("next")
            or self.request.POST.get("next")
            or ""
        )

class LessonDelete(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    Удаление занятия.

    Отвечает только на POST. GET возвращает 405.
    Подтверждение — через JS-confirm в форме.
    """

    model = Lesson
    http_method_names = ["post"]
    success_message = "Занятие удалено."

    def get_success_url(self):
        next_url = (
            self.request.GET.get("next")
            or self.request.POST.get("next")
            or ""
        )
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()},
        ):
            return next_url
        return reverse("timetable:lesson_list")

