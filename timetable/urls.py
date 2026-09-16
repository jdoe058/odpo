from django.urls import path

from . import views
from .view_lesson import lessons_list_view
from .exports.views import export_view

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path("lessons/", lessons_list_view, name="lessons_list"),
    path(
        "cycle/<int:cycle_id>/export/<slug:kind>/",
        export_view,
        name="cycle_export",
    ),
]
