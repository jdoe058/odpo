"""Создание записи справочника."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView

from timetable.references.forms import get_form_class

from .mixins import ReferenceSpecMixin


class ReferenceCreate(LoginRequiredMixin, ReferenceSpecMixin, CreateView):
    template_name = "timetable/references/reference_form.html"

    def get_form_class(self):
        return get_form_class(self.kwargs["slug"])

    def get_initial(self):
        return _initial_from_get(self.request, self.spec)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["spec"] = self.spec
        ctx["is_create"] = True
        return ctx

    def get_success_url(self):
        return reverse("timetable:reference_list", kwargs={"slug": self.kwargs["slug"]})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Запись создана.")

        if "_addanother" in self.request.POST:
            return redirect(_create_url_with_prefill(self.spec, self.object))
        return redirect(self.get_success_url())


def _initial_from_get(request, spec) -> dict:
    """Собирает initial из GET для полей add_another_prefill."""
    initial = {}
    for field_name in spec.add_another_prefill:
        if field_name not in request.GET:
            continue
        field = spec.model._meta.get_field(field_name)
        raw = request.GET.get(field_name, "")
        if raw == "":
            continue
        try:
            if field.is_relation:
                initial[field_name] = int(raw)
            elif field.get_internal_type() == "BooleanField":
                initial[field_name] = raw.lower() in ("1", "true", "on", "yes")
            else:
                initial[field_name] = raw
        except (TypeError, ValueError):
            continue
    return initial


def _create_url_with_prefill(spec, obj) -> str:
    """URL формы создания с предзаполнением из только что сохранённого объекта."""
    url = reverse("timetable:reference_create", kwargs={"slug": spec.slug})
    params = {}
    for field_name in spec.add_another_prefill:
        field = spec.model._meta.get_field(field_name)
        if field.is_relation:
            value = getattr(obj, f"{field_name}_id", None)
        elif field.get_internal_type() == "BooleanField":
            value = "1" if getattr(obj, field_name, False) else "0"
        else:
            value = getattr(obj, field_name, None)
        if value is None or value == "":
            continue
        params[field_name] = value

    if not params:
        return url
    return f"{url}?{urlencode(params)}"