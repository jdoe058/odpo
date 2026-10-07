from django.urls import include, path

from . import views
from .exports.pdf.pdf_views import export_pdf_view
from .exports.views import cycle_xlsx_export_view

app_name = "timetable"

urlpatterns = [
    path("", views.ScheduleGrid.as_view(), name="schedule_grid"),
    path("lessons/", include("timetable.lessons.urls")),
    path(
        "cycle/<int:cycle_id>/export/xlsx/",
        cycle_xlsx_export_view,
        name="cycle_export_xlsx",
    ),
    path(
        "cycle/<int:cycle_id>/export/<slug:kind>/",
        export_pdf_view,
        name="cycle_export",
    ),
    path("cycles/", include("timetable.cycles.urls")),
    path("references/", include("timetable.references.urls")),
    path(
        "cycle/import/",
        views.cycle_import_view,
        name="cycle_import",
    ),
    path(
        "cycle/import/template/",
        views.cycle_import_template_view,
        name="cycle_import_template",
    ),
    path("reports/ped-hours/", views.PedHoursReport.as_view(), name="ped_hours"),
    path(
        "reports/ped-hours/export/",
        views.ped_hours_export_view,
        name="ped_hours_export",
    ),
]
