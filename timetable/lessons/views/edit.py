"""Редактирование занятия."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import UpdateView

from timetable.models import Lesson

from ..forms import LessonForm


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