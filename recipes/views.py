from django.shortcuts import render
from .models import Recipe

# Create your views here.

def recipe_list(request):
    recipes = Recipe.objects.all().order_by("name")

    context = {
        "recipes": recipes,
    }

    return render(request, "recipes/recipe_list.html", context)
