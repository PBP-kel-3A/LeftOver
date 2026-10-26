from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RecipeForm
from .models import Ingredient, Recipe, RecipeIngredient

#Membatasi akses hanya untuk staff atau superuser.
def admin_required(view_func):
    return user_passes_test(
        lambda user: user.is_staff or user.is_superuser,
        login_url="main:login",
    )(view_func)

#parse bahan dengan format satu bahan per baris yang dipisahkan oleh "|" -> nama | takaran
def parse_ingredients(ingredients_text):
    """Parse bahan dengan format satu bahan per baris: nama | takaran."""
    ingredients = []
    seen = set()

    for line in ingredients_text.splitlines():
        line = line.strip()

        if not line:
            continue

        if "|" not in line:
            raise ValueError(
                f"Format bahan tidak valid: '{line}'. "
                "Gunakan format nama bahan | takaran."
            )

        name, measure = line.split("|", 1)
        name = name.strip()
        measure = measure.strip()

        if not name:
            raise ValueError("Nama bahan tidak boleh kosong.")

        if len(name) > 100:
            raise ValueError(
                f"Nama bahan '{name}' melebihi 100 karakter."
            )

        if len(measure) > 100:
            raise ValueError(
                f"Takaran untuk '{name}' melebihi 100 karakter."
            )

        normalized_name = name.casefold()

        if normalized_name in seen:
            raise ValueError(f"Bahan '{name}' ditulis lebih dari sekali.")

        seen.add(normalized_name)
        ingredients.append((name, measure))

    if not ingredients:
        raise ValueError("Minimal masukkan satu bahan.")

    return ingredients

#menyimpan relasi bahan dan takaran untuk suatu resep
def save_recipe_ingredients(recipe, ingredients):
    recipe.recipe_ingredients.all().delete()

    for name, measure in ingredients:
        ingredient, _ = Ingredient.objects.get_or_create(name=name)

        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            measure=measure,
        )


@login_required
def recipe_list(request):
    recipes = Recipe.objects.all().order_by("name")

    search_query = request.GET.get("search", "").strip()
    category_query = request.GET.get("category", "").strip()
    ingredient_query = request.GET.get("ingredients", "").strip()
 
    if search_query:
        recipes = recipes.filter(
            Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(area__icontains=search_query)
        )

    if category_query:
        recipes = recipes.filter(category=category_query)

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
        Recipe.objects.exclude(category__isnull=True)
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

    if request.headers.get("HX-Request") == "true":
        return render(
            request, "recipes/partials/recipe_cards.html", context
        )

    return render(request, "recipes/recipe_list.html", context)


@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    return render(
        request,
        "recipes/recipe_detail.html",
        {"recipe": recipe},
    )


@login_required
def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST)

        if form.is_valid():
            try:
                ingredients = parse_ingredients(
                    form.cleaned_data["ingredients_text"]
                )

                with transaction.atomic():
                    recipe = form.save(commit=False)
                    recipe.created_by = request.user
                    # Resep buatan user bukan data dari TheMealDB.
                    recipe.mealdb_id = None
                    recipe.save()

                    save_recipe_ingredients(recipe, ingredients)

                messages.success(request, "Resep berhasil ditambahkan.")
                return redirect("recipes:recipe_detail", pk=recipe.pk)

            except ValueError as error:
                form.add_error("ingredients_text", str(error))

    else:
        form = RecipeForm()

    return render(
        request,
        "recipes/recipe_form.html",
        {"form": form, "page_title": "Tambah Resep"},
    )


@login_required
@admin_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    existing_ingredients = "\n".join(
        f"{item.ingredient.name} | {item.measure or ''}"
        for item in recipe.recipe_ingredients.select_related("ingredient")
    )

    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)

        if form.is_valid():
            try:
                ingredients = parse_ingredients(
                    form.cleaned_data["ingredients_text"]
                )

                with transaction.atomic():
                    updated_recipe = form.save()
                    save_recipe_ingredients(updated_recipe, ingredients)

                messages.success(request, "Resep berhasil diperbarui.")
                return redirect(
                    "recipes:recipe_detail", pk=updated_recipe.pk
                )

            except ValueError as error:
                form.add_error("ingredients_text", str(error))

    else:
        form = RecipeForm(
            instance=recipe,
            initial={"ingredients_text": existing_ingredients},
        )

    return render(
        request,
        "recipes/recipe_form.html",
        {"form": form, "page_title": "Edit Resep", "recipe": recipe},
    )


@login_required
@admin_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Resep berhasil dihapus.")
        return redirect("recipes:recipe_list")

    return render(
        request,
        "recipes/recipe_confirm_delete.html",
        {"recipe": recipe},
    )
