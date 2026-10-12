"""Удаление записи справочника."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DeleteView

from .mixins import ReferenceSpecMixin


class ReferenceDelete(LoginRequiredMixin, ReferenceSpecMixin, DeleteView):
    template_name = "timetable/references/reference_confirm_delete.html"

    def get_queryset(self):
        return self.spec.model.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["spec"] = self.spec
        ctx["title"] = f"Удалить запись?"
        next_url = self.request.GET.get("next", "")
        ctx["cancel_url"] = next_url or reverse(
            "timetable:reference_list", kwargs={"slug": self.kwargs["slug"]},
        )
        return ctx

    def form_valid(self, form):
        obj = self.get_object()
        try:
            obj.delete()
        except ProtectedError:
            messages.error(
                self.request,
                f"Нельзя удалить «{obj}»: запись используется в других данных.",
            )
        else:
            messages.success(self.request, f"«{obj}» удалено.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("timetable:reference_list", kwargs={"slug": self.kwargs["slug"]})