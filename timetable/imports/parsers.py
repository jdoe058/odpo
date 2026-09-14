from datetime import date, datetime, time

_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y")


def as_date(value, row_idx: int) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Строка {row_idx}: не распознана дата {value!r}")


def parse_time(value: str, row_idx: int) -> time:
    s = str(value).strip().replace(".", ":")
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"Строка {row_idx}: неверный формат времени {value!r}")
    return time(int(parts[0]), int(parts[1]))


def parse_range(value, row_idx: int):
    if not value or "-" not in str(value):
        raise ValueError(f"Строка {row_idx}: неверный диапазон времени {value!r}")
    a, b = str(value).split("-", 1)
    return parse_time(a, row_idx), parse_time(b, row_idx)

