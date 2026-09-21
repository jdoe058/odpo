"""Выгрузка всех справочников в один CSV-файл."""
import csv
import io
from datetime import datetime

from .registry import Column, specs_in_import_order


def export_bytes() -> bytes:
    """
    Собирает все справочники в один CSV.

    Кодировка: UTF-8 с BOM (чтобы Excel открывал двойным кликом).
    Разделитель: «;». Перенос строк: CRLF.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")

    buf.write("# Справочники расписания\r\n")
    buf.write(f"# Выгружено: {datetime.now():%Y-%m-%d %H:%M}\r\n")
    buf.write("# Формат: v1\r\n")

    for spec in specs_in_import_order():
        buf.write("\r\n")
        buf.write(f"# {spec.title}\r\n")
        buf.write(f"[{spec.slug}]\r\n")
        writer.writerow([c.csv_header() for c in spec.columns])
        for obj in spec.model.objects.order_by("pk"):
            writer.writerow([_serialize(obj, c) for c in spec.columns])

    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def _serialize(obj, col: Column) -> str:
    if col.kind == "fk_name":
        related = getattr(obj, col.name, None)
        if related is None:
            return ""
        return str(getattr(related, col.fk_attr, ""))
    value = getattr(obj, col.name)
    if value is None:
        return ""
    if col.kind == "bool":
        return "true" if value else "false"
    return str(value)