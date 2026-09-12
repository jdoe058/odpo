from dataclasses import dataclass, field
from datetime import date, datetime, time
from io import BytesIO

from django.db import transaction
from openpyxl import load_workbook

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType, normalize_short_name
)


class ScheduleImportError(Exception):
    """Ошибка импорта — показывается пользователю как есть."""


@dataclass
class ImportResult:
    cycle: Cycle
    lessons_created: int
    warnings: list[str] = field(default_factory=list)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ScheduleImportError(f"Не удалось распознать дату: {value!r}")


def _parse_time(value: str) -> time:
    s = str(value).strip().replace(".", ":")
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"неверный формат времени: {value!r}")
    return time(int(parts[0]), int(parts[1]))


def _parse_range(value: str):
    if not value or "-" not in str(value):
        raise ValueError(f"неверный диапазон: {value!r}")
    a, b = str(value).split("-", 1)
    return _parse_time(a), _parse_time(b)


def _normalize_name(value) -> str:
    return " ".join(str(value).split()).upper()


def _resolve_or_error(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise ScheduleImportError(
            f"Справочник не заполнен: {model._meta.verbose_name} "
            f"с параметрами {kwargs}"
        )


@transaction.atomic
def import_schedule(file_obj) -> ImportResult:
    """
    Разбирает XLSX и записывает Cycle + Lessons.
    Бросает ScheduleImportError с человекочитаемым сообщением.
    """
    try:
        wb = load_workbook(BytesIO(file_obj.read()), data_only=True)
    except Exception as e:
        raise ScheduleImportError(f"Не удалось открыть файл: {e}")

    ws = wb.active

    # --- шапка ---
    compiled_name = _normalize_name(ws["A1"].value or "")
    funding_name = str(ws["A2"].value or "").strip()
    base_name = str(ws["A3"].value or "").strip()
    cycle_name_str = str(ws["A4"].value or "").strip()
    start_date = _as_date(ws["A5"].value)
    end_date = _as_date(ws["A6"].value)

    compiled_by = _resolve_or_error(Employee, short_name=compiled_name)
    funding = _resolve_or_error(FundingType, name=funding_name)
    base = _resolve_or_error(Base, name=base_name)
    cycle_name = _resolve_or_error(CycleName, name=cycle_name_str)

    cycle, created = Cycle.objects.get_or_create(
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

    warnings: list[str] = []
    created_count = 0

    for row_idx, row in enumerate(
        ws.iter_rows(min_row=7, values_only=True), start=7
    ):
        row = (row + (None,) * 6)[:6]
        date_val, time_range, hours, code, topic, teacher = row

        if not date_val and not teacher:
            continue  # полностью пустая строка

        try:
            lesson_date = _as_date(date_val)
        except ScheduleImportError:
            warnings.append(f"Строка {row_idx}: не распознана дата {date_val!r}")
            continue

        try:
            t_start, t_end = _parse_range(time_range)
        except (ValueError, TypeError):
            warnings.append(f"Строка {row_idx}: время {time_range!r}")
            continue

        try:
            hours_int = int(hours)
        except (TypeError, ValueError):
            warnings.append(f"Строка {row_idx}: часы {hours!r}")
            continue

        try:
            lesson_type = LessonType.objects.get(code=str(code).strip())
        except LessonType.DoesNotExist:
            warnings.append(
                f"Строка {row_idx}: тип занятия с кодом {code!r} не найден"
            )
            continue

        try:
            teacher_obj = Employee.objects.get(
                short_name=_normalize_name(teacher)
            )
        except Employee.DoesNotExist:
            warnings.append(
                f"Строка {row_idx}: сотрудник {teacher!r} не найден"
            )
            continue

        Lesson.objects.create(
            cycle=cycle,
            date=lesson_date,
            time_start=t_start,
            time_end=t_end,
            hours=hours_int,
            lesson_type=lesson_type,
            topic=str(topic or "").strip(),
            employee=teacher_obj,
        )
        created_count += 1

    return ImportResult(
        cycle=cycle,
        lessons_created=created_count,
        warnings=warnings,
    )