from django.shortcuts import render, get_object_or_404
from .models import Recipe
from django.db.models import Q

# Create your views here.

def recipe_list(request):
    recipes = Recipe.objects.all().order_by("name")

    search_query = request.GET.get("search", "").strip()
    category_query = request.GET.get("category", "").strip()
    ingredient_query = request.GET.get("ingredients", "").strip()

    # Search by recipe name, category, or area
    if search_query:
        recipes = recipes.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(area__icontains=search_query)
        )

    # Filter by category
    if category_query:
        recipes = recipes.filter(category=category_query)

    # Filter by available ingredients
    ingredient_queries = [
        ingredient.strip()
        for ingredient in ingredient_query.split(",")
        if ingredient.strip()
    ]

    for ingredient in ingredient_queries:
        recipes = recipes.filter(
            recipe_ingredients__ingredient__name__icontains=ingredient
        )

    recipes = recipes.distinct()

    categories = (
        Recipe.objects
        .exclude(category__isnull=True)
        .exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "recipes": recipes,
        "categories": categories,
        "search_query": search_query,
        "category_query": category_query,
        "ingredient_query": ingredient_query,
    }

    return render(request, "recipes/recipe_list.html", context)

def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    context = {
        "recipe": recipe,
    }

    return render(request, "recipes/recipe_detail.html", context)
