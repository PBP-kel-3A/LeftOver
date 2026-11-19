from django.urls import path
from . import api_views

urlpatterns = [
    path("auth/login/", api_views.login_api, name="login_api"),
    path("auth/register/", api_views.register_api, name="register_api"),
    path("auth/logout/", api_views.logout_api, name="logout_api"),
]