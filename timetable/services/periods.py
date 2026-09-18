from datetime import date, timedelta
from django.utils import timezone


def resolve_period(kind, today=None, start=None, end=None):
    """kind: 'week' | 'month' | 'year' | 'custom' → (start, end)."""
    if kind == "year":
        anchor = today or timezone.localdate()
        # учебный год: 1 сентября — 31 августа
        if anchor.month >= 9:
            start = date(anchor.year, 9, 1)
            end = date(anchor.year + 1, 8, 31)
        else:
            start = date(anchor.year - 1, 9, 1)
            end = date(anchor.year, 8, 31)
        return start, end

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
