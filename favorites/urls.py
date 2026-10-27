from django.urls import path
from . import views

app_name = "favorites"

urlpatterns = [
    path("", views.favorite_list, name="favorite_list"),
    path("add/<int:recipe_id>/", views.favorite_add, name="favorite_add"),
    path("<int:pk>/edit/", views.favorite_update, name="favorite_update"),
    path("<int:pk>/delete/", views.favorite_delete, name="favorite_delete"),
    path("json/", views.favorite_list_json, name="favorite_list_json"),
    path("toggle/<int:recipe_id>/", views.favorite_toggle, name="favorite_toggle"),
]
