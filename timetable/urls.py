from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("", views.schedule_grid_view, name="schedule_grid"),
    path("overtime/", views.overtime_view, name="overtime"),
]