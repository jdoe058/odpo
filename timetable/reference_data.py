"""
Канонические данные для начального заполнения справочников.

Модуль не зависит от Django — только структуры. Команда seed_references
превращает их в записи через get_or_create.

Важно: FUNDING_TYPES хранятся в нормализованном виде (UPPERCASE,
без лишних пробелов) — именно в таком виде их ищет импорт расписания
после normalize_name().
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSpec:
    name: str
    max_hours_per_day: int = 0
    can_sign: bool = False
    can_approve: bool = False
    sort_order: int = 100


@dataclass(frozen=True)
class DocumentKindSpec:
    code: str
    name: str
    sort_order: int = 100


@dataclass(frozen=True)
class LessonTypeSpec:
    code: str
    name: str
    category: str = ""        # "" | "lecture" | "seminar" | "practice"
    counts_in_hours: bool = True
    sort_order: int = 100


# --- Виды финансирования ------------------------------------------------

FUNDING_TYPES: tuple[str, ...] = (
    "БЮДЖЕТ",
    "ДОГОВОР",
)


# --- Должности ----------------------------------------------------------

POSITIONS: tuple[PositionSpec, ...] = (
    PositionSpec("директор", max_hours_per_day=0,
                 can_sign=True, can_approve=True, sort_order=10),
    PositionSpec("зам. директора по ДПО", max_hours_per_day=0,
                 can_sign=True, can_approve=True, sort_order=20),
    PositionSpec("зав. отделением", max_hours_per_day=0, 
                 can_sign=True, can_approve=False, sort_order=30),
    PositionSpec("преподаватель", max_hours_per_day=6, sort_order=50),
    PositionSpec("преподаватель-совместитель", max_hours_per_day=4, sort_order=60),
)


# --- Типы документов ----------------------------------------------------

# code должен совпадать с тем, что ищут экспортёры:
# timetable/exports/schedule.py::get_active_template("schedule")
# timetable/exports/teacher_load.py::get_active_template("teacher_load")
DOCUMENT_KINDS: tuple[DocumentKindSpec, ...] = (
    DocumentKindSpec("schedule",        "Расписание",                           sort_order=10),
    DocumentKindSpec("teacher_load",    "Распределение часов преподавателей",   sort_order=20),
    DocumentKindSpec("timesheet",       "Табель учета рабочего времени",        sort_order=30),
)


# --- Типы занятий -------------------------------------------------------

LESSON_TYPES: tuple[LessonTypeSpec, ...] = (
    LessonTypeSpec("0",  "лекция",                      category="lecture",     counts_in_hours=True, sort_order=10),
    LessonTypeSpec("7",  "занятие семинарского типа 1", category="seminar",     counts_in_hours=True, sort_order=11),
    LessonTypeSpec("8",  "занятие семинарского типа 2", category="seminar",     counts_in_hours=True, sort_order=12),
    LessonTypeSpec("10", "занятие семинарского типа 3", category="seminar",     counts_in_hours=True, sort_order=13),
    LessonTypeSpec("1",  "практика 1",                  category="practice",    counts_in_hours=True, sort_order=21),
    LessonTypeSpec("2",  "практика 2",                  category="practice",    counts_in_hours=True, sort_order=22),
    LessonTypeSpec("3",  "практика 3",                  category="practice",    counts_in_hours=True, sort_order=23),
    LessonTypeSpec("4",  "практика 4",                  category="practice",    counts_in_hours=True, sort_order=24),
    LessonTypeSpec("5",  "практика 5",                  category="practice",    counts_in_hours=True, sort_order=25),
    LessonTypeSpec("6",  "практика 6",                  category="practice",    counts_in_hours=True, sort_order=26),        
    LessonTypeSpec("9",  "итоговая аттестация",         category="",            counts_in_hours=True, sort_order=30),
)