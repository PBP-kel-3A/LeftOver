from django.urls import path

from . import views

app_name = "shopping"

urlpatterns = [
    path("", views.shopping_list, name="shopping_list"),
    path("add/", views.shopping_add, name="shopping_add"),
    path("<int:pk>/toggle/", views.shopping_toggle, name="shopping_toggle"),
    path("<int:pk>/delete/", views.shopping_delete, name="shopping_delete"),
    path("transfer/", views.transfer_to_pantry, name="transfer_to_pantry"),
]
