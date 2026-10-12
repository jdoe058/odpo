"""Проверка нестыковок в расписании: разрывы и накладки внутри групп."""
from collections import defaultdict
from datetime import date, time


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _group_label(group: str) -> str:
    if group:
        return f"группа {group}"
    return "без группы"

def _default_break() -> int:
    """Дефолтная перемена из модели Lesson."""
    from timetable.models import Lesson

    return Lesson._meta.get_field("break_after_minutes").default

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

def recalculate_breaks(lessons) -> int:
    """
    Проставляет break_after_minutes по фактическому промежутку между
    соседними занятиями одной группы за один день.

    Возвращает количество обновлённых занятий.

    Правила:
    * последнее занятие дня у группы — перемена 0;
    * если промежуток отрицательный (накладка) — не трогаем, чтобы
      ошибка оставалась видна в блоке нестыковок;
    * если промежуток уже совпадает — не трогаем.
    """
    from timetable.models import Lesson

    buckets: dict[tuple, list] = defaultdict(list)
    for lesson in lessons:
        buckets[(lesson.date, lesson.group)].append(lesson)

    to_update: list = []

    for items in buckets.values():
        items.sort(key=lambda l: l.time_start)
        for i, prev in enumerate(items):
            if i == len(items) - 1:
                new_value = _default_break()
            else:
                next_ = items[i + 1]
                gap = (
                    _to_minutes(next_.time_start)
                    - _to_minutes(prev.time_end)
                )
                if gap < 0:
                    continue
                new_value = gap

            if prev.break_after_minutes != new_value:
                prev.break_after_minutes = new_value
                to_update.append(prev)

    if to_update:
        Lesson.objects.bulk_update(to_update, ["break_after_minutes"])

    return len(to_update)

