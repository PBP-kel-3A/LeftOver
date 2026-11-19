from django.urls import path
from . import api_views

urlpatterns = [
    path("reviews/", api_views.review_api_list, name="review_api_list"),
    path("reviews/<int:pk>/", api_views.review_api_detail, name="review_api_detail"),
]