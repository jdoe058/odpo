"""
Демонстрационные данные: базы, сотрудники, названия циклов, циклы и занятия.

Используются management-командой seed_demo для быстрого наполнения БД
на стендах разработки и в демо-окружении. Все значения вымышленные.

Модуль не зависит от Django — только структуры. Команда превращает
их в записи через get_or_create.

Позиции сотрудников и коды типов занятий должны существовать в
reference_data (POSITIONS, LESSON_TYPES) — их ставит seed_references.
"""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BaseSpec:
    name: str


@dataclass(frozen=True)
class EmployeeSpec:
    short_name: str
    position: str       # PositionSpec.name из reference_data


@dataclass(frozen=True)
class CycleNameSpec:
    name: str


@dataclass(frozen=True)
class LessonSpec:
    day: int            # смещение в днях от start_date цикла
    time_start: str     # "HH:MM"
    hours: int
    lesson_type_code: str       # LessonTypeSpec.code
    topic: str
    employee: str               # EmployeeSpec.short_name


@dataclass(frozen=True)
class CycleSpec:
    name: str           # CycleNameSpec.name
    funding: str        # FUNDING_TYPES
    base: str           # BaseSpec.name
    start_date: date
    end_date: date
    compiled_by: str    # EmployeeSpec.short_name
    lessons: tuple[LessonSpec, ...]


# --- Базы ---------------------------------------------------------------

BASES: tuple[BaseSpec, ...] = (
    BaseSpec("УЧЕБНЫЙ КОРПУС №1"),
    BaseSpec("УЧЕБНЫЙ КОРПУС №2"),
    BaseSpec("ВЫЕЗДНОЙ КЛАСС"),
)


# --- Сотрудники ---------------------------------------------------------

EMPLOYEES: tuple[EmployeeSpec, ...] = (
    EmployeeSpec("ОРЛОВ И.М.", "зам. директора по ДПО"),
    EmployeeSpec("ГОЛУБЕВА А.С.", "зав. отделением"),
    EmployeeSpec("МАРКОВ Д.В.", "преподаватель"),
    EmployeeSpec("СОКОЛОВА Е.Н.", "преподаватель"),
    EmployeeSpec("НОВИКОВА Т.Ю.", "преподаватель"),
    EmployeeSpec("ЛЕБЕДЕВ П.А.", "преподаватель-совместитель"),
)


# --- Названия циклов ----------------------------------------------------

CYCLE_NAMES: tuple[CycleNameSpec, ...] = (
    CycleNameSpec("ОХРАНА ТРУДА ДЛЯ РУКОВОДИТЕЛЕЙ"),
    CycleNameSpec("ПОЖАРНАЯ БЕЗОПАСНОСТЬ"),
    CycleNameSpec("ЭЛЕКТРОБЕЗОПАСНОСТЬ, III ГРУППА"),
    CycleNameSpec("ОКАЗАНИЕ ПЕРВОЙ ПОМОЩИ"),
    CycleNameSpec("ОБРАЩЕНИЕ С ОТХОДАМИ I–IV КЛАССОВ"),
)


# --- Занятия: helper ----------------------------------------------------

def _lessons(
    *,
    days: tuple[int, ...],
    teachers: tuple[str, ...],
    topics: tuple[str, ...],
    types: tuple[str, ...] = ("0", "7", "1", "7", "0"),
    time_start: str = "09:00",
    hours: int = 2,
) -> tuple[LessonSpec, ...]:
    """
    Раскладывает занятия по дням, циклично перебирая типы, темы и
    преподавателей. Последнее занятие в списке всегда — итоговая
    аттестация (код «9»), чтобы демо-цикл выглядел законченным.
    """
    result = [
        LessonSpec(
            day=day,
            time_start=time_start,
            hours=hours,
            lesson_type_code=types[i % len(types)],
            topic=topics[i % len(topics)],
            employee=teachers[i % len(teachers)],
        )
        for i, day in enumerate(days)
    ]
    last = result[-1]
    result[-1] = LessonSpec(
        day=last.day, time_start=last.time_start, hours=last.hours,
        lesson_type_code="9", topic="Итоговая аттестация",
        employee=last.employee,
    )
    return tuple(result)


# --- Циклы --------------------------------------------------------------

CYCLES: tuple[CycleSpec, ...] = (
    CycleSpec(
        name="ОХРАНА ТРУДА ДЛЯ РУКОВОДИТЕЛЕЙ",
        funding="БЮДЖЕТ",
        base="УЧЕБНЫЙ КОРПУС №1",
        start_date=date(2026, 8, 24),
        end_date=date(2026, 9, 4),
        compiled_by="ОРЛОВ И.М.",
        lessons=_lessons(
            days=(0, 1, 2, 3, 4, 7, 8, 9, 10, 11),
            teachers=("МАРКОВ Д.В.", "СОКОЛОВА Е.Н."),
            topics=(
                "Основы охраны труда",
                "Правовые основы охраны труда",
                "Опасные производственные факторы",
                "Средства индивидуальной защиты",
                "Обучение и инструктажи",
                "Организация безопасных условий труда",
                "Расследование несчастных случаев",
                "Оказание первой помощи",
                "Документация по охране труда",
                "Практическое занятие",
            ),
        ),
    ),
    CycleSpec(
        name="ПОЖАРНАЯ БЕЗОПАСНОСТЬ",
        funding="ДОГОВОР",
        base="УЧЕБНЫЙ КОРПУС №2",
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 25),
        compiled_by="ГОЛУБЕВА А.С.",
        lessons=_lessons(
            days=(0, 1, 2, 3, 4, 7, 8, 9, 10, 11),
            teachers=("НОВИКОВА Т.Ю.", "ЛЕБЕДЕВ П.А."),
            topics=(
                "Причины пожаров",
                "Классификация пожаров",
                "Средства тушения",
                "Пожарная сигнализация",
                "Эвакуация людей",
                "Пожарная безопасность зданий",
                "Действия при пожаре",
                "Первая помощь пострадавшим",
                "Практическое занятие",
                "Документация",
            ),
        ),
    ),
    CycleSpec(
        name="ЭЛЕКТРОБЕЗОПАСНОСТЬ, III ГРУППА",
        funding="БЮДЖЕТ",
        base="ВЫЕЗДНОЙ КЛАСС",
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 23),
        compiled_by="ШЕРОЗИЯ И.М.",
        lessons=_lessons(
            days=(0, 1, 2, 3, 4, 7, 8, 9, 10, 11),
            teachers=("МАРКОВ Д.В.", "ЛЕБЕДЕВ П.А."),
            topics=(
                "Действие электрического тока на человека",
                "Электробезопасность на производстве",
                "Заземление и зануление",
                "Защитные средства",
                "Организационные мероприятия",
                "Технические мероприятия",
                "Оказание первой помощи при поражении током",
                "Практическое занятие",
                "Оформление наряда-допуска",
                "Разбор ситуаций",
            ),
        ),
    ),
)
