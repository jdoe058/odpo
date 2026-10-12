"""Специальные действия над занятием: inline-правка ячейки и пересчёт перемен."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from timetable.models import Lesson
from timetable.schedule_filter import ScheduleFilterForm
from timetable.services.lesson_gaps import recalculate_breaks

from ..forms import LessonInlineForm
from ._helpers import build_lessons


INLINE_EDITABLE_FIELDS = frozenset({
    "date", "time_start", "hours", "break_after_minutes",
    "category", "group", "topic",
})


@login_required
def lesson_cell_update(request, pk: int, field: str):
    """Обновляет одно поле занятия. Отдаёт HTML ячейки для HTMX."""
    if field not in INLINE_EDITABLE_FIELDS:
        raise Http404(f"Поле «{field}» нельзя редактировать inline")

    lesson = get_object_or_404(
        Lesson.objects.select_related("cycle", "cycle__base", "employee"),
        pk=pk,
    )

    error = ""

    if request.method == "POST":
        form = LessonInlineForm(request.POST, instance=lesson, field_name=field)
        if form.is_valid():
            lesson = form.save()
            response = render(request, "timetable/lessons/_inline_cell.html", {
                "lesson": lesson,
                "field": field,
                "error": "",
            })
            response["HX-Refresh"] = "true"
            return response
        else:
            field_errors = form.errors.get(field, [])
            error = "; ".join(str(e) for e in field_errors)
            lesson.refresh_from_db()

    return render(request, "timetable/lessons/_inline_cell.html", {
        "lesson": lesson,
        "field": field,
        "error": error,
    })


@login_required
@require_POST
def lesson_recalculate_breaks(request):
    """Проставляет break_after_minutes по фактическим промежуткам."""
    form = ScheduleFilterForm(request.POST)
    form.is_valid()
    data = form.cleaned_data

    lessons = build_lessons(data)
    count = recalculate_breaks(lessons)

    if count:
        messages.success(request, f"{count} перемен обновлено.")
    else:
        messages.info(request, "Перемен не требовалось менять.")

    next_url = request.POST.get("next") or reverse("timetable:lesson_list")
    return redirect(next_url)