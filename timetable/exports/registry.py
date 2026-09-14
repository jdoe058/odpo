from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class ExporterSpec:
    code: str          # слаг для URL и kind.code
    label: str         # подпись кнопки
    view: str          # dotted path до view
    url_slug: str      # суффикс admin-роута: <object_id>/export-<slug>/


EXPORTERS: tuple[ExporterSpec, ...] = (
    ExporterSpec(
        code="schedule",
        label="Расписание",
        view="timetable.exports.views.schedule_export_view",
        url_slug="schedule",
    ),
    ExporterSpec(
        code="teacher_load",
        label="Распределение часов",
        view="timetable.exports.views.teacher_load_export_view",
        url_slug="teacher-load",
    ),
)


def resolve_view(dotted_path: str):
    module_path, _, attr = dotted_path.rpartition(".")
    if not module_path:
        raise ValueError(f"Некорректный путь до view: {dotted_path!r}")
    return getattr(import_module(module_path), attr)


def admin_url_name(spec: ExporterSpec) -> str:
    return f"timetable_cycle_export_{spec.code}"

