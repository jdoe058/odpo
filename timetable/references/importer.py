"""
Разбор CSV-файла справочников и применение к БД.

Двухшаговый сценарий:
* parse_and_validate(content) — только чтение, отчёт об ошибках;
* apply(content) — повторный разбор + запись в одной транзакции.
"""
import re
import csv
from dataclasses import dataclass, field

from django.db import transaction

from .registry import ReferenceSpec, get_spec, specs_in_import_order


SLUG_RE = re.compile(r"^\[([a-z][a-z0-9_]*)\]\s*$")


@dataclass
class ParseResult:
    rows: dict[str, list[dict]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def parse_and_validate(content: bytes) -> ParseResult:
    result = ParseResult()
    lines = content.decode("utf-8-sig").splitlines()

    current_spec: ReferenceSpec | None = None
    current_columns: list | None = None
    section_seen: set[str] = set()
    last_order = -1
    sections_found = 0

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = SLUG_RE.match(line)
        if match:
            if current_spec is not None and current_columns is None:
                result.errors.append(
                    f"строка {line_no}: у секции [{current_spec.slug}] "
                    "отсутствует строка заголовков"
                )
            slug = match.group(1)
            current_spec, current_columns, last_order, sections_found = _enter_section(
                slug, line_no, result, section_seen, last_order, sections_found,
            )
            continue

        if current_spec is None:
            result.warnings.append(
                f"строка {line_no}: данные вне секции — пропущены"
            )
            continue

        if current_columns is None:
            current_columns = _parse_header(line, line_no, current_spec, result)
            continue

        _parse_row(line, line_no, current_spec, current_columns, result)

    if current_spec is not None and current_columns is None:
        result.errors.append(
            f"у секции [{current_spec.slug}] отсутствует строка заголовков"
        )
    if sections_found == 0:
        result.errors.append("в файле не найдено ни одной известной секции")

    return result


def apply(content: bytes) -> ParseResult:
    result = parse_and_validate(content)
    if result.errors:
        return result

    with transaction.atomic():
        for spec in specs_in_import_order():
            rows = result.rows.get(spec.slug, [])
            for row in rows:
                obj = spec.model.objects.get(pk=row["_pk"])
                for key, value in row.items():
                    if key == "_pk":
                        continue
                    setattr(obj, key, value)
                obj.save()
            if rows:
                result.stats[spec.slug] = len(rows)
    return result


# --- Внутреннее ---------------------------------------------------------

def _enter_section(slug, line_no, result, section_seen, last_order, sections_found):
    spec = get_spec(slug)
    if spec is None:
        result.warnings.append(
            f"строка {line_no}: неизвестная секция [{slug}] — пропущена"
        )
        return None, None, last_order, sections_found
    if slug in section_seen:
        result.errors.append(
            f"строка {line_no}: секция [{slug}] встречается дважды"
        )
        return None, None, last_order, sections_found
    if spec.import_order < last_order:
        result.errors.append(
            f"строка {line_no}: секция [{slug}] нарушает порядок "
            f"(ожидался порядок не меньше {last_order})"
        )
        return None, None, last_order, sections_found
    section_seen.add(slug)
    return spec, None, spec.import_order, sections_found + 1


def _parse_header(line, line_no, spec, result):
    names = [n.strip() for n in _csv_fields(line)]
    by_header = {c.csv_header(): c for c in spec.columns}
    columns: list = []
    for name in names:
        col = by_header.get(name)
        if col is None:
            result.warnings.append(
                f"строка {line_no}: [{spec.slug}] неизвестная колонка "
                f"«{name}» — пропущена"
            )
            columns.append(None)
        else:
            columns.append(col)
    return columns


def _parse_row(line, line_no, spec, columns, result):
    values = _csv_fields(line)
    if len(values) != len(columns):
        result.warnings.append(
            f"строка {line_no}: [{spec.slug}] ожидалось {len(columns)} полей, "
            f"получено {len(values)} — строка пропущена"
        )
        return

    row: dict = {}
    for col, raw in zip(columns, values):
        if col is None:
            continue
        try:
            row[col.name] = _convert(col, raw)
        except ValueError as exc:
            result.warnings.append(
                f"строка {line_no}: [{spec.slug}] поле «{col.name}»: "
                f"{exc} — строка пропущена"
            )
            return

    if not _resolve_foreign_key(row, line_no, spec, columns, result):
        return
    if not _resolve_upsert_key(row, line_no, spec, result):
        return

    result.rows.setdefault(spec.slug, []).append(row)


def _convert(col, raw):
    value = raw.strip()
    if col.kind == "str":
        return value
    if col.kind == "int":
        if value == "":
            raise ValueError("пустое значение")
        return int(value)
    if col.kind == "int_nullable":
        return None if value == "" else int(value)
    if col.kind == "bool":
        low = value.lower()
        if low in ("true", "1", "да", "yes"):
            return True
        if low in ("false", "0", "нет", "no", ""):
            return False
        raise ValueError(f"не удалось разобрать boolean: {value!r}")
    if col.kind == "fk_name":
        return value
    raise ValueError(f"неизвестный тип колонки «{col.kind}»")

def _csv_fields(line: str) -> list[str]:
    """Разбирает одну CSV-строку с учётом кавычек и ; внутри полей."""
    return next(csv.reader([line], delimiter=";"))

def _resolve_foreign_key(row, line_no, spec, columns, result) -> bool:
    for col in columns:
        if col is None or col.kind != "fk_name":
            continue
        value = row.get(col.name)
        if not value:
            field = spec.model._meta.get_field(col.name)
            if field.null:
                del row[col.name]
                row[col.name + "_id"] = None
                continue
            result.errors.append(
                f"строка {line_no}: [{spec.slug}] поле «{col.name}» пусто"
            )
            return False
        related_model = spec.model._meta.get_field(col.name).related_model
        related = related_model.objects.filter(**{col.fk_attr: value}).first()
        if related is None:
            result.warnings.append(
                f"строка {line_no}: [{spec.slug}] {col.name}=«{value}» "
                "не найдено — строка пропущена"
            )
            return False
        del row[col.name]
        row[col.name + "_id"] = related.pk
    return True


def _resolve_upsert_key(row, line_no, spec, result) -> bool:
    key_value = row.get(spec.upsert_key)
    if spec.key_normalizer is not None and key_value is not None:
        key_value = spec.key_normalizer(key_value)
        row[spec.upsert_key] = key_value
    if not key_value:
        result.errors.append(
            f"строка {line_no}: [{spec.slug}] пустое значение ключа "
            f"«{spec.upsert_key}»"
        )
        return False
    obj = spec.model.objects.filter(**{spec.upsert_key: key_value}).first()
    if obj is None:
        result.errors.append(
            f"строка {line_no}: [{spec.slug}] запись с "
            f"{spec.upsert_key}=«{key_value}» не найдена"
        )
        return False
    row["_pk"] = obj.pk
    return True