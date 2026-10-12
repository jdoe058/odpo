"""Создание занятия."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView

from timetable.models import Lesson

from ..forms import LessonForm


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
                    "category": prev.category,
                    "group": prev.group,
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