from django.apps import AppConfig


class TimetableConfig(AppConfig):
    name = "timetable"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Импорт наполняет реестр выгрузок (exports/kinds.py).
        from timetable.exports import schedule, teacher_load, timesheet  # noqa: F401