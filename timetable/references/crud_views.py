"""Универсальные CRUD-вью для справочников из реестра."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import get_form_class
from .registry import get_spec


def _spec_or_404(slug: str):
    spec = get_spec(slug)
    if spec is None:
        raise Http404(f"Неизвестный справочник: {slug!r}")
    return spec


@login_required
def reference_list(request, slug):
    spec = _spec_or_404(slug)
    q = (request.GET.get("q") or "").strip()

    qs = spec.model.objects.all()
    if q:
        cond = Q()
        for col in spec.columns:
            if col.kind == "str":
                cond |= Q(**{f"{col.name}__icontains": q})
            elif col.kind == "fk_name":
                cond |= Q(**{f"{col.name}__{col.fk_attr}__icontains": q})
        if cond:
            qs = qs.filter(cond)

    return render(request, "timetable/references/reference_list.html", {
        "spec": spec,
        "objects": qs,
        "q": q,
    })


@login_required
def reference_create(request, slug):
    spec = _spec_or_404(slug)
    form_class = get_form_class(slug)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Запись создана.")
            return redirect("timetable:reference_list", slug=slug)
    else:
        form = form_class()

    return render(request, "timetable/references/reference_form.html", {
        "spec": spec,
        "form": form,
        "is_create": True,
    })


@login_required
def reference_edit(request, slug, pk):
    spec = _spec_or_404(slug)
    obj = get_object_or_404(spec.model, pk=pk)
    form_class = get_form_class(slug)

    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("timetable:reference_list", slug=slug)
    else:
        form = form_class(instance=obj)

    return render(request, "timetable/references/reference_form.html", {
        "spec": spec,
        "form": form,
        "object": obj,
        "is_create": False,
    })


@login_required
@require_POST
def reference_delete(request, slug, pk):
    spec = _spec_or_404(slug)
    obj = get_object_or_404(spec.model, pk=pk)

    try:
        obj.delete()
    except ProtectedError:
        messages.error(
            request,
            f"Нельзя удалить «{obj}»: запись используется в других данных.",
        )
    else:
        messages.success(request, f"«{obj}» удалено.")

    return redirect("timetable:reference_list", slug=slug)