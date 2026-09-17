from datetime import date, timedelta
from django.db.models import Max, Min
from django.utils import timezone


def resolve_period(kind, today=None, start=None, end=None, cycle=None):
    """kind: 'week' | 'month' | 'custom' | 'all' → (start, end)."""
    from timetable.models import Lesson

    if kind == "all":
        if cycle is not None:
            return cycle.start_date, cycle.end_date

        qs = Lesson.objects.all()
        agg = qs.aggregate(first=Min("date"), last=Max("date"))
        if agg["first"] and agg["last"]:
            return agg["first"], agg["last"]

        # если занятий нет — текущая неделя
        today = today or timezone.localdate()
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    today = today or timezone.localdate()

    if kind == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    if kind == "month":
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return start, end

    if kind == "custom":
        if not start or not end:
            raise ValueError("custom period requires start and end")
        if end < start:
            start, end = end, start
        return start, end

    raise ValueError(f"unknown period kind: {kind!r}")
