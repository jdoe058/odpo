from django.urls import path

from . import views
from .exports import views as export_views

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path(
        "cycle/<int:object_id>/schedule.docx",
        export_views.schedule_export_view,
        name="cycle_export_schedule_docx",
    ),
    path(
        "cycle/<int:object_id>/teacher-load.docx",
        export_views.teacher_load_export_view,
        name="cycle_export_teacher_load_docx",
    ),
]