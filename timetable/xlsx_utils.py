"""Общие утилиты для чтения XLSX."""
from datetime import date, datetime, time

from openpyxl import load_workbook


def load_from_upload(file_obj):
    """Открывает XLSX из UploadedFile. data_only=True — только значения, не формулы."""
    return load_workbook(file_obj, data_only=True)


def cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def cell_date(value) -> date | None:
    """Принимает datetime, date или строку. Форматы: YYYY-MM-DD, DD.MM.YYYY."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
    return None


def cell_time(value) -> time | None:
    """Принимает datetime, time или строку. Форматы: HH:MM, HH:MM:SS, HH.MM."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        s = value.strip().replace(".", ":")
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).time()
            except ValueError:
                pass
    return None


def cell_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None