from django.contrib import admin
from .models import Recipe, Ingredient, RecipeIngredient

# Mendafkarkan model ke Django Admin
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(RecipeIngredient)