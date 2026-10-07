from django.urls import path

from .views import LessonCreate, LessonEdit, LessonList

urlpatterns = [
    path("", LessonList.as_view(), name="lesson_list"),
    path("new/", LessonCreate.as_view(), name="lesson_create"),
    path("<int:pk>/edit/", LessonEdit.as_view(), name="lesson_edit"),
]