"""CBV для CRUD циклов."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, ListView, UpdateView,
)

from timetable.models import Cycle, Lesson

from .forms import CycleFilterForm, CycleForm


class CycleList(LoginRequiredMixin, ListView):
    model = Cycle
    template_name = "timetable/cycles/cycle_list.html"
    context_object_name = "cycles"

    def get_queryset(self):
        qs = (
            Cycle.objects
            .select_related("name", "base", "funding_type", "compiled_by")
            .order_by("-start_date")
        )

        self.filter_form = CycleFilterForm(self.request.GET)
        if not self.filter_form.is_valid():
            return qs

        q = (self.filter_form.cleaned_data.get("q") or "").strip()
        base = self.filter_form.cleaned_data.get("base")

        if q:
            qs = qs.filter(
                Q(name__name__icontains=q) | Q(base__name__icontains=q)
            )
        if base is not None:
            qs = qs.filter(base=base)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not hasattr(self, "filter_form"):
            self.filter_form = CycleFilterForm(self.request.GET)
        ctx["form"] = self.filter_form
        return ctx


class CycleCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Cycle
    form_class = CycleForm
    template_name = "timetable/cycles/cycle_form.html"
    success_url = reverse_lazy("timetable:cycle_list")
    success_message = "Цикл создан."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_create"] = True
        return ctx


class CycleEdit(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Cycle
    form_class = CycleForm
    template_name = "timetable/cycles/cycle_form.html"
    success_url = reverse_lazy("timetable:cycle_list")
    success_message = "Изменения сохранены."

    def get_queryset(self):
        return Cycle.objects.select_related(
            "name", "base", "funding_type", "compiled_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_create"] = False
        return ctx


class CycleDelete(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Cycle
    template_name = "timetable/cycles/cycle_confirm_delete.html"
    success_url = reverse_lazy("timetable:cycle_list")
    success_message = "Цикл удалён."

    def get_queryset(self):
        return Cycle.objects.select_related("name", "base")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lessons_count"] = Lesson.objects.filter(
            cycle=self.get_object(),
        ).count()
        return ctx