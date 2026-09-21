"""Выгрузка цикла и его занятий в CSV."""
import csv
import io
from datetime import datetime

from timetable.models import Cycle


CYCLE_FIELDS = ("compiled_by", "funding", "base", "name", "start_date", "end_date")
LESSON_HEADER = (
    "date", "time_start", "hours", "lesson_type_code",
    "topic", "employee", "break_after_minutes", "base",
)


def cycle_to_csv_bytes(cycle: Cycle) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")

    buf.write(f"# Цикл: {cycle.name.name}\r\n")
    buf.write("[cycle]\r\n")
    writer.writerow(["compiled_by", cycle.compiled_by.short_name])
    writer.writerow(["funding", cycle.funding_type.name])
    writer.writerow(["base", cycle.base.name])
    writer.writerow(["name", cycle.name.name])
    writer.writerow(["start_date", cycle.start_date.isoformat()])
    writer.writerow(["end_date", cycle.end_date.isoformat()])

    buf.write("\r\n")
    buf.write("# Занятия\r\n")
    buf.write("[lessons]\r\n")
    writer.writerow(LESSON_HEADER)

    lessons = (
        cycle.lessons
        .select_related("lesson_type", "employee", "base")
        .order_by("date", "time_start")
    )
    for lesson in lessons:
        writer.writerow([
            lesson.date.isoformat(),
            lesson.time_start.strftime("%H:%M"),
            lesson.hours,
            lesson.lesson_type.code,
            lesson.topic or "",
            lesson.employee.short_name,
            lesson.break_after_minutes,
            lesson.base.name if lesson.base_id else "",
        ])

    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")