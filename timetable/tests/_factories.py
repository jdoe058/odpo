"""
Хелперы для тестов. Не тесты — общие фабрики.

Импорты моделей — локальные, внутри функций. Причина: `_factories`
может импортироваться на этапе, когда приложения ещё не загружены
(например, из `conftest`-подобных мест). Локальный импорт гарантирует,
что модели доступны только в момент вызова, когда Django уже готов.
"""

# --- Модели справочников ---------------------------------------------

def make_position(
    name: str,
    *,
    max_hours_per_day: int = 0,
    max_hours_per_week: int | None = None,
    max_hours_per_year: int | None = None,
    can_sign: bool = False,
    can_approve: bool = False,
    sort_order: int = 100,
):
    from timetable.models import Position
    return Position.objects.create(
        name=name,
        max_hours_per_day=max_hours_per_day,
        max_hours_per_week=max_hours_per_week,
        max_hours_per_year=max_hours_per_year,
        can_sign=can_sign,
        can_approve=can_approve,
        sort_order=sort_order,
    )


def make_employee(short_name: str, position):
    from timetable.models import Employee
    return Employee.objects.create(short_name=short_name, position=position)


def make_base(name: str):
    from timetable.models import Base
    return Base.objects.create(name=name)


def make_funding_type(name: str):
    from timetable.models import FundingType
    return FundingType.objects.create(name=name)


def make_cycle_name(name: str):
    from timetable.models import CycleName
    return CycleName.objects.create(name=name)


def make_cycle(*, name, base, funding, compiled_by, start_date, end_date):
    from timetable.models import Cycle
    return Cycle.objects.create(
        name=name,
        base=base,
        funding_type=funding,
        compiled_by=compiled_by,
        start_date=start_date,
        end_date=end_date,
    )

