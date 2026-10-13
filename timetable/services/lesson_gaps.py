"""Проверка нестыковок в расписании: разрывы и накладки внутри групп."""
from collections import defaultdict
from datetime import time

from timetable.models import Lesson


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _group_label(group: str) -> str:
    if group:
        return f"группа {group}"
    return "без группы"


def _default_break() -> int:
    """Дефолтная перемена из модели Lesson."""
    return Lesson._meta.get_field("break_after_minutes").default


def _build_streams(day_lessons: list) -> dict[str, list]:
    """
    Разбивает занятия дня на потоки по группам.

    Поток группы = её занятия + общие занятия (group="") того же дня.
    Если в дне есть хотя бы одна группа — отдельного потока "" нет,
    потому что общие занятия уже входят в потоки каждой группы.
    Если групп нет — единственный поток "" из общих занятий.
    """
    day_groups = {l.group for l in day_lessons if l.group}

    if day_groups:
        return {
            g: [l for l in day_lessons if l.group == g or l.group == ""]
            for g in day_groups
        }

    return {"": list(day_lessons)}


def find_lesson_gaps(lessons) -> list[str]:
    """
    Проверяет стыковку занятий внутри потока каждой группы за день.

    Поток группы = её занятия + общие занятия (group="").
    """
    lessons = list(lessons)

    by_date: dict = defaultdict(list)
    for lesson in lessons:
        by_date[lesson.date].append(lesson)

    messages: list[str] = []

    for lesson_date, day_lessons in by_date.items():
        streams = _build_streams(day_lessons)

        for group, stream in streams.items():
            stream.sort(key=lambda l: l.time_start)

            for prev, next_ in zip(stream, stream[1:]):
                expected = _to_minutes(prev.available_from)
                actual = _to_minutes(next_.time_start)
                diff = actual - expected
                if diff == 0:
                    continue

                kind = "разрыв" if diff > 0 else "накладка"
                delta = abs(diff)
                messages.append(
                    f"{lesson_date:%d.%m.%Y}, {_group_label(group)}: "
                    f"{kind} {delta} мин между "
                    f"{prev.time_start:%H:%M} и {next_.time_start:%H:%M}"
                )

    messages.sort()
    return messages


def recalculate_breaks(lessons) -> int:
    """
    Проставляет break_after_minutes по фактическому промежутку между
    соседними занятиями в потоке группы за день.

    Возвращает количество обновлённых занятий.

    Правила:
    * последнее занятие потока — дефолтная перемена;
    * если промежуток отрицательный (накладка) — не трогаем;
    * если значение уже совпадает — не трогаем;
    * общее занятие, попавшее в несколько потоков, обрабатывается один раз.
    """
    lessons = list(lessons)

    by_date: dict = defaultdict(list)
    for lesson in lessons:
        by_date[lesson.date].append(lesson)

    new_breaks: dict[int, int] = {}

    for day_lessons in by_date.values():
        streams = _build_streams(day_lessons)

        for stream in streams.values():
            stream.sort(key=lambda l: l.time_start)

            for i, prev in enumerate(stream):
                if prev.pk in new_breaks:
                    continue

                if i == len(stream) - 1:
                    new_breaks[prev.pk] = _default_break()
                    continue

                next_ = stream[i + 1]
                gap = (
                    _to_minutes(next_.time_start)
                    - _to_minutes(prev.time_end)
                )
                if gap < 0:
                    continue
                new_breaks[prev.pk] = gap

    to_update: list[Lesson] = []
    for lesson in lessons:
        if lesson.pk not in new_breaks:
            continue
        new_value = new_breaks[lesson.pk]
        if lesson.break_after_minutes != new_value:
            lesson.break_after_minutes = new_value
            to_update.append(lesson)

    if to_update:
        Lesson.objects.bulk_update(to_update, ["break_after_minutes"])

    return len(to_update)