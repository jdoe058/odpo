"""Список записей справочника."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from timetable.references.forms import ReferenceSearchForm

from .mixins import ReferenceSpecMixin


class ReferenceList(LoginRequiredMixin, ReferenceSpecMixin, ListView):
    template_name = "timetable/references/reference_list.html"
    context_object_name = "objects"

    def get_queryset(self):
        qs = self.spec.model.objects.all()

        form = ReferenceSearchForm(self.request.GET)
        if not form.is_valid():
            return qs

        q = (form.cleaned_data.get("q") or "").strip()
        if not q:
            return qs

        cond = Q()
        for col in self.spec.searchable_columns():
            if col.kind == "str":
                cond |= Q(**{f"{col.name}__icontains": q})
            elif col.kind == "fk_name":
                cond |= Q(**{f"{col.name}__{col.fk_attr}__icontains": q})
        if cond:
            qs = qs.filter(cond)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = ReferenceSearchForm(self.request.GET)
        form.is_valid()

        ctx.update({
            "spec": self.spec,
            "form": form,
            "q": (form.cleaned_data.get("q") or "").strip(),
            "columns": self.spec.visible_columns(),
        })
        return ctx