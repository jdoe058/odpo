"""
Реестр справочников: единый источник истины для меню, обмена CSV
и (в будущем) CRUD-страниц.

Не импортирует Django-настройки сам — только модели. Загружается
только тогда, когда Django уже готов (после apps.ready).
"""
from dataclasses import dataclass
from typing import Callable

from timetable.models import (
    Base, CycleName, Employee, FundingType, LessonType, Position,
    normalize_short_name,
)


@dataclass(frozen=True)
class Column:
    """Колонка CSV, привязанная к полю модели."""

    name: str
    kind: str               # str | int | int_nullable | bool | fk_name
    header: str = ""
    fk_attr: str = "name"   # для kind="fk_name": по какому полю искать

    def csv_header(self) -> str:
        return self.header or self.name


@dataclass(frozen=True)
class ReferenceSpec:
    slug: str               # маркер [slug] в CSV, латиница
    title: str              # человекочитаемое название (комментарий, меню)
    model: type
    upsert_key: str         # по какому полю искать существующую запись
    import_order: int       # порядок секций в файле (жёсткий)
    columns: tuple[Column, ...]
    key_normalizer: Callable[[str], str] | None = None


SPECS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        slug="positions",
        title="Должности",
        model=Position,
        upsert_key="name",
        import_order=10,
        columns=(
            Column("name", "str", header="Название"),
            Column("max_hours_per_day", "int", header="Макс. часов в день"),
            Column("max_hours_per_week", "int_nullable", header="Макс. часов в неделю"),
            Column("max_hours_per_year", "int_nullable", header="Макс. часов в учебном году"),
            Column("can_sign", "bool", header="Подписывает"),
            Column("can_approve", "bool", header="Утверждает"),
            Column("sort_order", "int", header="Порядок сортировки"),
        ),
    ),
    ReferenceSpec(
        slug="employees",
        title="Сотрудники",
        model=Employee,
        upsert_key="short_name",
        import_order=20,
        columns=(
            Column("short_name", "str", header="Фамилия и инициалы"),
            Column("position", "fk_name", header="Должность"),
            Column("base", "fk_name", header="База"),
        ),
        key_normalizer=normalize_short_name,
    ),
    ReferenceSpec(
        slug="bases",
        title="Базы",
        model=Base,
        upsert_key="name",
        import_order=15,
        columns=(Column("name", "str", header="Название"),),
    ),
    ReferenceSpec(
        slug="funding_types",
        title="Виды финансирования",
        model=FundingType,
        upsert_key="name",
        import_order=40,
        columns=(Column("name", "str", header="Название"),),
    ),
    ReferenceSpec(
        slug="cycle_names",
        title="Названия циклов",
        model=CycleName,
        upsert_key="name",
        import_order=50,
        columns=(Column("name", "str", header="Название"),),
    ),
    ReferenceSpec(
        slug="lesson_types",
        title="Типы занятий",
        model=LessonType,
        upsert_key="code",
        import_order=60,
        columns=(
            Column("code", "str", header="Код"),
            Column("name", "str", header="Название"),
            Column("category", "str", header="Категория"),
            Column("counts_in_hours", "bool", header="Учитывать часы"),
            Column("sort_order", "int", header="Порядок сортировки"),
        ),
    ),
)

def all_specs() -> tuple[ReferenceSpec, ...]:
    return SPECS


def get_spec(slug: str) -> ReferenceSpec | None:
    for spec in SPECS:
        if spec.slug == slug:
            return spec
    return None


def specs_in_import_order() -> tuple[ReferenceSpec, ...]:
    return tuple(sorted(SPECS, key=lambda s: s.import_order))