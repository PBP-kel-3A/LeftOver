
from django.urls import path

from . import api_views


urlpatterns = [
    path(
        "pantry/",
        api_views.pantry_api_list,
        name="pantry_api_list"
    ),

    path(
        "pantry/<int:pk>/",
        api_views.pantry_api_detail,
        name="pantry_api_detail"
    ),
]
