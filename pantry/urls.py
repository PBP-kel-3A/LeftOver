from django.urls import path

from . import views

app_name = "pantry"

urlpatterns = [
    path("", views.pantry_list, name="pantry_list"),
    path("<int:pk>/edit/", views.pantry_edit, name="pantry_edit"),
    path("<int:pk>/delete/", views.pantry_delete, name="pantry_delete"),
    path("cari-resep/", views.find_recipes, name="find_recipes"),
]
