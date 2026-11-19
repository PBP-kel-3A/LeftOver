
from django.urls import path
from . import api_views

urlpatterns = [
    path("recipes/", api_views.recipe_api_list, name="recipe_api_list"),
    path("recipes/<int:pk>/", api_views.recipe_api_detail, name="recipe_api_detail"),
]
