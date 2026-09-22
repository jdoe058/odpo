"""Выгрузка цикла и его занятий в XLSX."""
import io

from openpyxl import Workbook

from timetable.models import Cycle, Lesson
from timetable.cycle_xlsx_import import (
    CYCLE_FIELDS, LESSON_FIELDS, SHEET_CYCLE, SHEET_LESSONS,
)


def cycle_to_xlsx_bytes(cycle: Cycle) -> bytes:
    wb = Workbook()

    ws = wb.worksheets[0]
    ws.title = SHEET_CYCLE
    ws.append(["Русское", "Латиница", "Значение"])

    values = {
        "compiled_by": cycle.compiled_by.short_name,
        "funding": cycle.funding_type.name,
        "base": cycle.base.name,
        "name": cycle.name.name,
        "start_date": cycle.start_date.isoformat(),
        "end_date": cycle.end_date.isoformat(),
    }
    for latin, ru in CYCLE_FIELDS:
        ws.append([ru, latin, values.get(latin, "")])

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 40

    ws2 = wb.create_sheet(SHEET_LESSONS)
    ws2.append([ru for _, ru in LESSON_FIELDS])
    ws2.append([latin for latin, _ in LESSON_FIELDS])

    default_break = Lesson._meta.get_field("break_after_minutes").default

    lessons = (
        Lesson.objects
        .filter(cycle=cycle)
        .select_related("lesson_type", "employee", "base")
        .order_by("date", "time_start")
    )

    for lesson in lessons:
        break_after = (
            "" if lesson.break_after_minutes == default_break
            else lesson.break_after_minutes
        )
        ws2.append([
            lesson.date.isoformat(),
            lesson.time_start.strftime("%H:%M"),
            lesson.hours,
            lesson.lesson_type.code,
            lesson.topic or "",
            lesson.employee.short_name,
            break_after,
            _get_base_name(lesson),
        ])

    for i in range(1, len(LESSON_FIELDS) + 1):
        ws2.column_dimensions[chr(64 + i)].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def _get_base_name(lesson) -> str:
    base = getattr(lesson, "base", None)
    return getattr(base, "name", "") if base is not None else ""