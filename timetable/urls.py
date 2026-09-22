from django.urls import path

from . import views
from .exports.views import cycle_export_csv_view, export_view
from .references import views as references_views

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path(
        "lessons/<int:pk>/edit/",
        views.lesson_edit_view,
        name="lesson_edit",
    ),
    path("templates/", views.template_library_view, name="template_library"),
    path("templates/<int:pk>/delete/", views.template_delete_view, name="template_delete"),
    path(
        "cycle/<int:cycle_id>/export/csv/",
        cycle_export_csv_view,
        name="cycle_export_csv",
    ),
    path(
        "cycle/<int:cycle_id>/export/<slug:kind>/",
        export_view,
        name="cycle_export",
    ),
    path("references/", references_views.exchange_view, name="references_exchange"),
    path("references/export/", references_views.export_view, name="references_export"),
    path("references/<slug:slug>/", references_views.reference_stub_view, name="reference_stub"),
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
]
