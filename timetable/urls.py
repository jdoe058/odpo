from django.urls import path

from . import views
from .exports.views import export_view

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path(
        "cycle/<int:cycle_id>/export/<slug:kind>/",
        export_view,
        name="cycle_export",
    ),
]
