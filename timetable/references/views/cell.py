"""Обновление одной ячейки справочника через HTMX."""
from functools import lru_cache

from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from timetable.references.inline import get_inline_value
from timetable.references.registry import get_spec


@lru_cache(maxsize=None)
def _get_single_field_form(slug: str, field: str):
    """ModelForm только с одним полем."""
    spec = get_spec(slug)
    if spec is None:
        raise ValueError(f"Unknown reference slug: {slug!r}")
    return modelform_factory(spec.model, fields=[field])


@login_required
def reference_cell_update(request, slug: str, pk: int, field: str):
    spec = get_spec(slug)
    if spec is None:
        raise Http404(f"Неизвестный справочник: {slug!r}")

    col = next((c for c in spec.columns if c.name == field), None)
    if col is None:
        raise Http404(f"Неизвестная колонка: {field!r}")

    obj = get_object_or_404(spec.model, pk=pk)
    error = ""

    if request.method == "POST":
        FormClass = _get_single_field_form(slug, field)
        form = FormClass(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
        else:
            field_errors = form.errors.get(field, [])
            error = "; ".join(str(e) for e in field_errors)

    return render(request, "timetable/references/_inline_cell.html", {
                "spec": spec,
                "obj": obj,
                "col": col,
                "value": get_inline_value(obj, col),
                "error": "",
            })
