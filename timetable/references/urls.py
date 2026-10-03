from django.urls import path

from . import crud_views, views

urlpatterns = [
    path("", views.exchange_view, name="references_exchange"),
    path("export/", views.export_view, name="references_export"),

    # Внимание: специфичные пути до общего <slug:slug>/
    path("<slug:slug>/new/", crud_views.reference_create, name="reference_create"),
    path("<slug:slug>/<int:pk>/edit/", crud_views.reference_edit, name="reference_edit"),
    path("<slug:slug>/<int:pk>/delete/", crud_views.reference_delete, name="reference_delete"),
    path("<slug:slug>/", crud_views.reference_list, name="reference_list"),
]