from django.urls import path
from . import views
from main.views import login_user, logout_user, register_user

app_name = "main"

urlpatterns = [
    path("", views.landing, name="landing"),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('register/', register_user, name='register'),
]