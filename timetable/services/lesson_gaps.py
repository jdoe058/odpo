"""Проверка нестыковок в расписании: разрывы и накладки внутри групп."""
from collections import defaultdict
from datetime import date, time


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _group_label(group: str) -> str:
    if group:
        return f"группа {group}"
    return "без группы"


def find_lesson_gaps(lessons) -> list[str]:
    """
    Проверяет стыковку занятий внутри (дата, группа).

    Возвращает список коротких сообщений о разрывах и накладках.
    Занятия с пустой группой считаются отдельной полноценной группой.
    """
    # группируем по (дата, группа)
    buckets: dict[tuple[date, str], list] = defaultdict(list)
    for lesson in lessons:
        buckets[(lesson.date, lesson.group)].append(lesson)

    messages: list[str] = []

    for (lesson_date, group), items in buckets.items():
        items.sort(key=lambda l: l.time_start)
        for prev, next_ in zip(items, items[1:]):
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