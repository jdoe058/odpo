from django.urls import path

from .views import (
    ReferenceCreate, ReferenceDelete, ReferenceEdit, ReferenceList,
    exchange_view, export_view,
)

urlpatterns = [
    path("", exchange_view, name="references_exchange"),
    path("export/", export_view, name="references_export"),

    path("<slug:slug>/new/", ReferenceCreate.as_view(), name="reference_create"),
    path("<slug:slug>/<int:pk>/edit/", ReferenceEdit.as_view(), name="reference_edit"),
    path("<slug:slug>/<int:pk>/delete/", ReferenceDelete.as_view(), name="reference_delete"),
    path("<slug:slug>/", ReferenceList.as_view(), name="reference_list"),
]