"""Редактирование записи справочника."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import UpdateView

from timetable.references.forms import get_form_class

from .create import _create_url_with_prefill
from .mixins import ReferenceSpecMixin


class ReferenceEdit(LoginRequiredMixin, ReferenceSpecMixin, UpdateView):
    template_name = "timetable/references/reference_form.html"

    def get_queryset(self):
        return self.spec.model.objects.all()

    def get_form_class(self):
        return get_form_class(self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["spec"] = self.spec
        ctx["is_create"] = False
        return ctx

    def get_success_url(self):
        return reverse("timetable:reference_list", kwargs={"slug": self.kwargs["slug"]})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Изменения сохранены.")

        if "_addanother" in self.request.POST:
            return redirect(_create_url_with_prefill(self.spec, self.object))
        return redirect(self.get_success_url())