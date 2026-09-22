"""Импорт цикла из XLSX и генерация шаблона."""
from django.db import transaction

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType,
)
from timetable.xlsx_utils import (
    cell_date, cell_int, cell_str, cell_time, load_from_upload,
)
from timetable.xlsx_cycle_format import (
    CYCLE_FIELDS, CYCLE_LATIN, CYCLE_RU_TO_LATIN,
    LESSON_FIELDS, LESSON_LATIN_TO_INDEX,
    SHEET_CYCLE, SHEET_LESSONS,
)


class CycleImportError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


# --- Импорт -------------------------------------------------------------

def import_cycle_from_xlsx(file_obj) -> Cycle:
    wb = load_from_upload(file_obj)

    errors: list[str] = []
    if SHEET_CYCLE not in wb.sheetnames:
        errors.append(f"В файле нет листа «{SHEET_CYCLE}».")
    if SHEET_LESSONS not in wb.sheetnames:
        errors.append(f"В файле нет листа «{SHEET_LESSONS}».")
    if errors:
        raise CycleImportError(errors)

    cycle_data = _parse_cycle_sheet(wb[SHEET_CYCLE], errors)
    lesson_rows = _parse_lessons_sheet(wb[SHEET_LESSONS], errors)

    if errors:
        raise CycleImportError(errors)

    return _persist(cycle_data, lesson_rows)


def _parse_cycle_sheet(ws, errors: list[str]) -> dict:
    result: dict[str, str] = {}

    # Пропускаем строку 1 (заголовки колонок «Русское | Латиница | Значение»).
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        col_a = cell_str(row[0] if len(row) > 0 else None)
        col_b = cell_str(row[1] if len(row) > 1 else None)
        value = row[2] if len(row) > 2 else None

        if not col_a and not col_b:
            continue

        if col_b and col_b in CYCLE_LATIN:
            key = col_b
        elif col_a and col_a in CYCLE_RU_TO_LATIN:
            key = CYCLE_RU_TO_LATIN[col_a]
        else:
            errors.append(
                f"лист «{SHEET_CYCLE}», строка {row_idx}: "
                f"неизвестное поле «{col_a or col_b}»"
            )
            continue

        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        result[key] = value

    for latin, ru in CYCLE_FIELDS:
        if latin not in result:
            errors.append(f"лист «{SHEET_CYCLE}»: не заполнено поле «{ru}»")

    return result


def _parse_lessons_sheet(ws, errors: list[str]) -> list[tuple[int, dict]]:
    rows: list[tuple[int, dict]] = []

    # Строка 2 — латинская шапка.
    latin_header = [
        cell_str(c.value) for c in ws[2]
    ] if ws.max_row >= 2 else []

    if not latin_header:
        errors.append(f"лист «{SHEET_LESSONS}»: пустая строка заголовков")
        return rows

    col_index: dict[str, int] = {}
    for idx, name in enumerate(latin_header):
        if name in LESSON_LATIN_TO_INDEX:
            col_index[name] = idx

    missing = [
        ru for latin, ru in LESSON_FIELDS if latin not in col_index
    ]
    if missing:
        errors.append(
            f"лист «{SHEET_LESSONS}»: в шапке нет колонок: {', '.join(missing)}"
        )
        return rows

    prev_date = None
    for row_idx, row in enumerate(
        ws.iter_rows(min_row=3, values_only=True), start=3
    ):
        if all(cell_str(v) == "" for v in row):
            continue
        row_data = {}
        for latin, idx in col_index.items():
            row_data[latin] = row[idx] if idx < len(row) else None

        # Пустая ячейка даты означает «тот же день, что и в предыдущей строке».
        if cell_str(row_data.get("date")) == "":
            row_data["date"] = prev_date
        else:
            prev_date = row_data["date"]

        rows.append((row_idx, row_data))

    return rows


def _persist(cycle_data: dict, lesson_rows: list[tuple[int, dict]]) -> Cycle:
    errors: list[str] = []

    cycle_name = CycleName.objects.filter(name=cell_str(cycle_data["name"])).first()
    if cycle_name is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: название цикла «{cycle_data['name']}» не найдено"
        )

    funding = FundingType.objects.filter(
        name=cell_str(cycle_data["funding"])
    ).first()
    if funding is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: финансирование "
            f"«{cycle_data['funding']}» не найдено"
        )

    base = Base.objects.filter(name=cell_str(cycle_data["base"])).first()
    if base is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: база «{cycle_data['base']}» не найдена"
        )

    compiled_by = Employee.objects.filter(
        short_name=cell_str(cycle_data["compiled_by"])
    ).first()
    if compiled_by is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: составитель "
            f"«{cycle_data['compiled_by']}» не найден"
        )

    start_date = cell_date(cycle_data["start_date"])
    if start_date is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: дата начала "
            f"«{cycle_data['start_date']}» не распознана"
        )

    end_date = cell_date(cycle_data["end_date"])
    if end_date is None:
        errors.append(
            f"лист «{SHEET_CYCLE}»: дата окончания "
            f"«{cycle_data['end_date']}» не распознана"
        )

    if errors:
        raise CycleImportError(errors)

    assert cycle_name is not None
    assert base is not None

    if Cycle.objects.filter(
        name=cycle_name, base=base, start_date=start_date
    ).exists():
        raise CycleImportError([
            f"Цикл «{cycle_name.name}» на базе «{base.name}» "
            f"с {start_date:%d.%m.%Y} уже существует."
        ])

    lesson_objects, lesson_errors = _build_lessons(lesson_rows)
    if lesson_errors:
        raise CycleImportError(lesson_errors)

    with transaction.atomic():
        cycle = Cycle.objects.create(
            name=cycle_name,
            funding_type=funding,
            base=base,
            start_date=start_date,
            end_date=end_date,
            compiled_by=compiled_by,
        )
        for lesson in lesson_objects:
            lesson.cycle = cycle
        Lesson.objects.bulk_create(lesson_objects)

    return cycle


def _build_lessons(rows: list[tuple[int, dict]]) -> tuple[list[Lesson], list[str]]:
    errors: list[str] = []
    lessons: list[Lesson] = []
    seen: set[tuple] = set()

    for row_idx, row in rows:
        lesson_date = cell_date(row.get("date"))
        if lesson_date is None:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                f"дата «{cell_str(row.get('date'))}» не распознана"
            )
            continue

        lesson_time = cell_time(row.get("time_start"))
        if lesson_time is None:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                f"время «{cell_str(row.get('time_start'))}» не распознано"
            )
            continue

        hours = cell_int(row.get("hours"))
        if hours is None or hours <= 0:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                f"часы «{cell_str(row.get('hours'))}» не распознаны"
            )
            continue

        type_code = cell_str(row.get("lesson_type_code"))
        lesson_type = LessonType.objects.filter(code=type_code).first()
        if lesson_type is None:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                f"код типа занятия «{type_code}» не найден"
            )
            continue

        emp_name = cell_str(row.get("employee"))
        employee = Employee.objects.filter(short_name=emp_name).first()
        if employee is None:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                f"преподаватель «{emp_name}» не найден"
            )
            continue

        break_after = cell_int(row.get("break_after_minutes"))
        if break_after is None:
            break_after = 10

        lesson_base = None
        base_name = cell_str(row.get("base"))
        if base_name:
            lesson_base = Base.objects.filter(name=base_name).first()
            if lesson_base is None:
                errors.append(
                    f"лист «{SHEET_LESSONS}», строка {row_idx}: "
                    f"база занятия «{base_name}» не найдена"
                )
                continue

        key = (lesson_date, lesson_time, employee.pk)
        if key in seen:
            errors.append(
                f"лист «{SHEET_LESSONS}», строка {row_idx}: конфликт — "
                f"у {employee.short_name} {lesson_date:%d.%m.%Y} "
                f"{lesson_time:%H:%M} занятие уже есть в файле"
            )
            continue
        seen.add(key)

        lessons.append(Lesson(
            date=lesson_date,
            time_start=lesson_time,
            hours=hours,
            lesson_type=lesson_type,
            topic=cell_str(row.get("topic")),
            employee=employee,
            break_after_minutes=break_after,
            base=lesson_base,
        ))

    return lessons, errors
