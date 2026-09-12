from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time
from io import BytesIO

from django.db import transaction
from openpyxl import load_workbook

import re
from collections import defaultdict


from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType,
    normalize_name, normalize_short_name,
)


class ScheduleImportError(Exception):
    """Ошибки импорта — список человекочитаемых сообщений."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class ParsedLesson:
    row_idx: int
    date: date
    time_start: time
    time_end: time
    hours: int
    lesson_type: LessonType
    topic: str
    employee: Employee


@dataclass
class ImportResult:
    cycle: Cycle
    lessons_created: int


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------

_LINE_RE = re.compile(r"^Строка (\d+): (.*)$")

def _as_date(value, row_idx: int):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"Строка {row_idx}: не распознана дата {value!r}")


def _parse_time(value: str, row_idx: int) -> time:
    s = str(value).strip().replace(".", ":")
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"Строка {row_idx}: неверный формат времени {value!r}")
    return time(int(parts[0]), int(parts[1]))


def _parse_range(value, row_idx: int):
    if not value or "-" not in str(value):
        raise ValueError(f"Строка {row_idx}: неверный диапазон времени {value!r}")
    a, b = str(value).split("-", 1)
    return _parse_time(a, row_idx), _parse_time(b, row_idx)

_LINE_RE = re.compile(r"^Строка (\d+): (.*)$")


def _compress_ranges(numbers: list[int]) -> str:
    """[9,10,11,12,17] → 'строки 9–12, 17'."""
    if not numbers:
        return ""
    ranges = []
    start = prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append((start, prev))
        start = prev = n
    ranges.append((start, prev))

    parts = [str(a) if a == b else f"{a}–{b}" for a, b in ranges]
    return "строки " + ", ".join(parts)


def _group_errors(errors: list[str]) -> list[str]:
    """
    Группирует однотипные ошибки, отбрасывая номер строки из ключа.
    'Строка 9: сотрудник X не найден' +
    'Строка 10: сотрудник X не найден'
    → 'сотрудник X не найден — строки 9, 10'
    """
    grouped: dict[str, list[int]] = defaultdict(list)
    ungrouped: list[str] = []

    for err in errors:
        m = _LINE_RE.match(err)
        if m:
            row = int(m.group(1))
            msg = m.group(2)
            grouped[msg].append(row)
        else:
            ungrouped.append(err)

    result = []
    for msg, rows in grouped.items():
        rows = sorted(set(rows))
        result.append(f"{msg} — {_compress_ranges(rows)}")
    result.extend(ungrouped)
    return result


def import_schedule(file_obj) -> ImportResult:
    """
    Разбирает XLSX. Если есть хоть одна ошибка — ничего не пишет в БД,
    а бросает ScheduleImportError со списком ошибок.
    """
    try:
        wb = load_workbook(BytesIO(file_obj.read()), data_only=True)
    except Exception as e:
        raise ScheduleImportError([f"Не удалось открыть файл: {e}"])

    ws = wb.active

    # --- Фаза 1: шапка ---
    errors: list[str] = []

    compiled_name = normalize_short_name(ws["A1"].value)
    funding_name = normalize_name(ws["A2"].value)
    base_name = normalize_name(ws["A3"].value)
    cycle_name_str = normalize_name(ws["A4"].value)

    try:
        start_date = _as_date(ws["A5"].value, row_idx=5)
    except ValueError as e:
        errors.append(str(e))
        start_date = None
    try:
        end_date = _as_date(ws["A6"].value, row_idx=6)
    except ValueError as e:
        errors.append(str(e))
        end_date = None

    compiled_by = Employee.objects.filter(short_name=compiled_name).first()
    if compiled_by is None:
        errors.append(f"Сотрудник не найден: {compiled_name!r}")

    funding = FundingType.objects.filter(name=funding_name).first()
    if funding is None:
        errors.append(f"Вид финансирования не найден: {funding_name!r}")

    base = Base.objects.filter(name=base_name).first()
    if base is None:
        errors.append(f"База не найдена: {base_name!r}")

    cycle_name = CycleName.objects.filter(name=cycle_name_str).first()
    if cycle_name is None:
        errors.append(f"Название цикла не найдено: {cycle_name_str!r}")

    # --- Фаза 2: занятия ---
    parsed: list[ParsedLesson] = []
    cache_types = {lt.code: lt for lt in LessonType.objects.all()}
    cache_employees = {e.short_name: e for e in Employee.objects.all()}

    for row_idx, row in enumerate(
        ws.iter_rows(min_row=7, values_only=True), start=7
    ):
        row = (row + (None,) * 6)[:6]
        date_val, time_range, hours, code, topic, teacher = row

        if not date_val and not teacher:
            continue

        try:
            lesson_date = _as_date(date_val, row_idx)
        except ValueError as e:
            errors.append(str(e))
            continue

        try:
            t_start, t_end = _parse_range(time_range, row_idx)
        except (ValueError, TypeError) as e:
            errors.append(str(e))
            continue

        try:
            hours_int = int(hours)
        except (TypeError, ValueError):
            errors.append(f"Строка {row_idx}: не распознаны часы {hours!r}")
            continue

        code_str = str(code).strip()
        lesson_type = cache_types.get(code_str)
        if lesson_type is None:
            errors.append(
                f"Строка {row_idx}: тип занятия с кодом {code_str!r} не найден"
            )
            continue

        teacher_name = normalize_short_name(teacher)
        teacher_obj = cache_employees.get(teacher_name)
        if teacher_obj is None:
            errors.append(
                f"Строка {row_idx}: сотрудник {teacher_name!r} не найден"
            )
            continue

        parsed.append(ParsedLesson(
            row_idx=row_idx,
            date=lesson_date,
            time_start=t_start,
            time_end=t_end,
            hours=hours_int,
            lesson_type=lesson_type,
            topic=str(topic or "").strip(),
            employee=teacher_obj,
        ))

    # --- Фаза 3: если есть ошибки — ни одной записи ---
    if errors:
        raise ScheduleImportError(_group_errors(errors))

    # --- Фаза 4: пишем всё одной транзакцией ---
    with transaction.atomic():
        cycle, _ = Cycle.objects.get_or_create(
            name=cycle_name,
            start_date=start_date,
            end_date=end_date,
            defaults={
                "funding_type": funding,
                "base": base,
                "compiled_by": compiled_by,
            },
        )
        cycle.lessons.all().delete()

        Lesson.objects.bulk_create([
            Lesson(
                cycle=cycle,
                date=p.date,
                time_start=p.time_start,
                time_end=p.time_end,
                hours=p.hours,
                lesson_type=p.lesson_type,
                topic=p.topic,
                employee=p.employee,
            )
            for p in parsed
        ])

    return ImportResult(cycle=cycle, lessons_created=len(parsed))