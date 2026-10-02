"""
Исторический модуль для миграций.

Модель DocumentTemplate удалена (см. миграцию <0009>).
Здесь остаётся только `template_upload_path` — на него ссылается
0001_initial.py, и Django не может загрузить граф миграций без него.

Не добавлять сюда модели и не импортировать этот модуль из
timetable/models.py — иначе Django попытается пересоздать таблицу.
"""


def template_upload_path(instance, filename: str) -> str:
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ext = filename.rsplit(".", 1)[-1].lower()
    kind = getattr(instance, "kind", None) or "unknown"
    return f"templates_docx/{kind}/{ts}_{kind}.{ext}"