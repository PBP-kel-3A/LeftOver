
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods

from recipes.models import Recipe
from .models import Favorite
from .forms import FavoriteNoteForm


# Helper: mengecek apakah request berasal dari AJAX
def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


# READ: Menampilkan semua resep favorit milik user
@login_required
def favorite_list(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related("recipe")
        .order_by("-created_at")
    )

    category = request.GET.get("category", "").strip()

    if category:
        favorites = favorites.filter(
            recipe__category__iexact=category
        )

    # Pilihan kategori dari resep yang difavoritkan user
    categories = (
        Recipe.objects
        .filter(favorited_by__user=request.user)
        .exclude(category__isnull=True)
        .exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "favorites": favorites,
        "categories": categories,
        "selected_category": category,
    }

    return render(request, "favorites/favorite_list.html", context)


# CREATE: Menambahkan resep ke favorit
@login_required
@require_POST
def favorite_add(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        recipe=recipe
    )

    if is_ajax(request):
        return JsonResponse({
            "success": True,
            "is_favorited": True,
            "created": created,
            "recipe_id": recipe.id,
            "message": (
                "Resep ditambahkan ke favorit."
                if created
                else "Resep sudah ada di favorit."
            )
        })

    return redirect("favorites:favorite_list")


# UPDATE: Mengedit catatan pribadi pada favorit
@login_required
@require_http_methods(["GET", "POST"])
def favorite_update(request, pk):
    favorite = get_object_or_404(
        Favorite,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        form = FavoriteNoteForm(request.POST, instance=favorite)

        if form.is_valid():
            form.save()

            if is_ajax(request):
                return JsonResponse({
                    "success": True,
                    "favorite_id": favorite.id,
                    "personal_note": favorite.personal_note,
                    "message": "Catatan berhasil diperbarui!"
                })

            return redirect("favorites:favorite_list")

        if is_ajax(request):
            return JsonResponse({
                "success": False,
                "errors": form.errors.get_json_data()
            }, status=400)

    else:
        form = FavoriteNoteForm(instance=favorite)

    return render(
        request,
        "favorites/favorite_form.html",
        {
            "form": form,
            "favorite": favorite
        }
    )


# DELETE: Menghapus resep dari favorit
@login_required
@require_POST
def favorite_delete(request, pk):
    favorite = get_object_or_404(
        Favorite,
        pk=pk,
        user=request.user
    )

    recipe_id = favorite.recipe_id
    favorite.delete()

    if is_ajax(request):
        return JsonResponse({
            "success": True,
            "is_favorited": False,
            "recipe_id": recipe_id,
            "message": "Resep berhasil dihapus dari favorit!"
        })

    return redirect("favorites:favorite_list")


# READ JSON: Mengambil data favorit milik user
@login_required
def favorite_list_json(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related("recipe")
        .order_by("-created_at")
    )

    category = request.GET.get("category", "").strip()

    if category:
        favorites = favorites.filter(
            recipe__category__iexact=category
        )

    data = [
        {
            "id": favorite.id,
            "recipe_id": favorite.recipe_id,
            "recipe_name": favorite.recipe.name,
            "recipe_image": favorite.recipe.image_url,
            "recipe_category": favorite.recipe.category,
            "personal_note": favorite.personal_note,
            "created_at": favorite.created_at.isoformat(),
        }
        for favorite in favorites
    ]

    return JsonResponse({
        "success": True,
        "count": len(data),
        "favorites": data
    })
