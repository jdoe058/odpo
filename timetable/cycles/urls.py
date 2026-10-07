from django.urls import path

from .views import CycleCreate, CycleDelete, CycleEdit, CycleList

urlpatterns = [
    path("", CycleList.as_view(), name="cycle_list"),
    path("new/", CycleCreate.as_view(), name="cycle_create"),
    path("<int:pk>/edit/", CycleEdit.as_view(), name="cycle_edit"),
    path("<int:pk>/delete/", CycleDelete.as_view(), name="cycle_delete"),
]
