from django.urls import path

from . import views
from .exports.views import export_view

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
        "cycle/<int:cycle_id>/export/<slug:kind>/",
        export_view,
        name="cycle_export",
    ),
]
