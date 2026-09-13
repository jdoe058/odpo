from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path(
        "cycle/<int:cycle_id>/schedule.docx",
        views.schedule_export_view,
        name="cycle_export_schedule_docx",
    ),
    path(
        "cycle/<int:cycle_id>/teacher-load.docx",
        views.teacher_load_export_view,
        name="cycle_export_teacher_load_docx",
    ),
]