"""Удаление занятия."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DeleteView

from timetable.models import Lesson


class LessonDelete(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    Удаление занятия.

    GET — страница подтверждения, POST — удаление.
    """

    model = Lesson
    template_name = "timetable/lessons/lesson_confirm_delete.html"
    success_message = "Занятие удалено."

    def get_queryset(self):
        return Lesson.objects.select_related("cycle", "cycle__name", "employee")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Удалить занятие?"
        next_url = self.request.GET.get("next", "")
        ctx["cancel_url"] = next_url or reverse("timetable:lesson_list")
        return ctx

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