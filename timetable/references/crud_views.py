"""Универсальные CRUD-вью для справочников из реестра."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ReferenceSearchForm, get_form_class
from .registry import get_spec


def _spec_or_404(slug: str):
    spec = get_spec(slug)
    if spec is None:
        raise Http404(f"Неизвестный справочник: {slug!r}")
    return spec


@login_required
def reference_list(request, slug):
    spec = _spec_or_404(slug)

    form = ReferenceSearchForm(request.GET or None)
    q = ""
    if form.is_valid():
        q = form.cleaned_data.get("q", "").strip()

    qs = spec.model.objects.all()
    if q:
        cond = Q()
        for col in spec.searchable_columns():
            if col.kind == "str":
                cond |= Q(**{f"{col.name}__icontains": q})
            elif col.kind == "fk_name":
                cond |= Q(**{f"{col.name}__{col.fk_attr}__icontains": q})
        if cond:
            qs = qs.filter(cond)

    return render(request, "timetable/references/reference_list.html", {
        "spec": spec,
        "objects": qs,
        "form": form,
        "q": q,
        "columns": spec.visible_columns(),
    })

@login_required
def reference_create(request, slug):
    spec = _spec_or_404(slug)
    form_class = get_form_class(slug)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Запись создана.")
            if "_addanother" in request.POST:
                return _redirect_to_create(spec, obj)
            return redirect("timetable:reference_list", slug=slug)
    else:
        form = form_class(initial=_initial_from_get(request, spec))

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
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            if "_addanother" in request.POST:
                return _redirect_to_create(spec, obj)
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

def _redirect_to_create(spec, obj):
    """Ведёт на форму создания с предзаполнением из сохранённого объекта."""
    url = reverse("timetable:reference_create", kwargs={"slug": spec.slug})
    params = {}
    for field_name in spec.add_another_prefill:
        field = spec.model._meta.get_field(field_name)
        if field.is_relation:
            value = getattr(obj, f"{field_name}_id", None)
        elif field.get_internal_type() == "BooleanField":
            value = getattr(obj, field_name, False)
            value = "1" if value else "0"
        else:
            value = getattr(obj, field_name, None)

        if value is None or value == "":
            continue
        params[field_name] = value

    if not params:
        return redirect(url)
    return redirect(f"{url}?{urlencode(params)}")