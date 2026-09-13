from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Sum


CATEGORY_ORDER = ("lecture", "seminar", "practice")
CATEGORY_LABELS = {
    "lecture": "Лекции",
    "seminar": "Занятия семинарского типа",
    "practice": "Практика",
}


@dataclass(frozen=True)
class LoadRow:
    n: int
    teacher: str
    lecture: int
    seminar: int
    practice: int
    total: int


@dataclass(frozen=True)
class TeacherLoad:
    rows: tuple[LoadRow, ...]
    total_lecture: int
    total_seminar: int
    total_practice: int
    grand_total: int


def calculate_teacher_load(cycle) -> TeacherLoad:
    """
    Часы преподавателей по трём фиксированным категориям.
    Типы занятий без категории в отчёт не попадают.
    """
    data = (
        cycle.lessons
        .filter(lesson_type__counts_in_hours=True)
        .exclude(lesson_type__category="")
        .values("employee_id", "employee__short_name", "lesson_type__category")
        .annotate(h=Sum("hours"))
    )

    per_emp: dict[int, dict[str, int]] = defaultdict(lambda: {
        "lecture": 0, "seminar": 0, "practice": 0,
    })
    names: dict[int, str] = {}

    for r in data:
        cat = r["lesson_type__category"]
        if cat not in CATEGORY_ORDER:
            continue
        per_emp[r["employee_id"]][cat] += r["h"]
        names[r["employee_id"]] = r["employee__short_name"]

    rows: list[LoadRow] = []
    for n, emp_id in enumerate(
        sorted(per_emp.keys(), key=lambda e: names[e]), start=1
    ):
        cells = per_emp[emp_id]
        rows.append(LoadRow(
            n=n,
            teacher=names[emp_id],
            lecture=cells["lecture"],
            seminar=cells["seminar"],
            practice=cells["practice"],
            total=cells["lecture"] + cells["seminar"] + cells["practice"],
        ))

    t_lec = sum(r.lecture for r in rows)
    t_sem = sum(r.seminar for r in rows)
    t_prac = sum(r.practice for r in rows)

    return TeacherLoad(
        rows=tuple(rows),
        total_lecture=t_lec,
        total_seminar=t_sem,
        total_practice=t_prac,
        grand_total=t_lec + t_sem + t_prac,
    )