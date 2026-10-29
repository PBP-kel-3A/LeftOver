
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Avg, Count

from recipes.models import Recipe
from .forms import FavoriteNoteForm
from .models import Favorite


def is_ajax(request):
    """Cek apakah request dari frontend mengharapkan respons JSON (AJAX)."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def user_favorites(request):
    """Ambil favorit user beserta rating, jumlah review, dan filter kategori."""
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("recipe")
        .annotate(
            avg_rating=Avg("recipe__reviews__rating"),
            review_count=Count("recipe__reviews", distinct=True),
        )
    )

    category = request.GET.get("category", "").strip()

    if category:
        favorites = favorites.filter(recipe__category__iexact=category)

    return favorites


def add_favorite(user, recipe):
    """Ambil favorit yang sudah ada atau buat baru tanpa duplikasi."""
    return Favorite.objects.get_or_create(
        user=user,
        recipe=recipe
    )


@login_required
@require_GET
def favorite_list(request):
    # READ: Tampilkan seluruh resep favorit milik user.
    favorites = user_favorites(request)

    return render(request, "favorites/favorite_list.html", {
        "favorites": favorites,
    })


@login_required
@require_POST
def favorite_add(request, recipe_id):
    # CREATE: Tambahkan resep ke favorit tanpa membuat data duplikat.
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    favorite, created = add_favorite(request.user, recipe)

    if is_ajax(request):
        return JsonResponse({
            "success": True,
            "is_favorited": True,
            "created": created,
            "recipe_id": recipe.pk,
            "favorite_id": favorite.pk,
            "message": (
                "Resep ditambahkan ke favorit."
                if created
                else "Resep sudah ada di favorit."
            ),
        })

    return redirect("favorites:favorite_list")


@login_required
@require_http_methods(["GET", "POST"])
def favorite_update(request, pk):
    # UPDATE: Hanya pemilik favorit yang boleh mengubah catatan pribadinya.
    favorite = get_object_or_404(
        Favorite,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        form = FavoriteNoteForm(request.POST, instance=favorite)

        if form.is_valid():
            form.save()

            # Jika request berasal dari modal AJAX, kembalikan JSON.
            if is_ajax(request):
                return JsonResponse({
                    "success": True,
                    "favorite_id": favorite.pk,
                    "personal_note": favorite.personal_note,
                    "message": "Catatan berhasil diperbarui!",
                })

            # Jika menggunakan form biasa, kembali ke halaman Favorites.
            return redirect("favorites:favorite_list")

        # Kirim pesan error dalam bentuk JSON jika validasi AJAX gagal.
        if is_ajax(request):
            return JsonResponse({
                "success": False,
                "errors": form.errors.get_json_data(),
            }, status=400)

    else:
        # GET: Tampilkan form dengan catatan yang sudah tersimpan.
        form = FavoriteNoteForm(instance=favorite)

    return render(request, "favorites/favorite_form.html", {
        "form": form,
        "favorite": favorite,
    })


@login_required
@require_POST
def favorite_delete(request, pk):
    # DELETE: Hapus favorit milik user yang sedang login.
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
            "message": "Resep berhasil dihapus dari favorit!",
        })

    return redirect("favorites:favorite_list")


@login_required
@require_GET
def favorite_list_json(request):
    # READ JSON: Kembalikan seluruh favorit user dalam format JSON.
    favorites = user_favorites(request)

    data = [
        {
            "id": favorite.pk,
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
        "favorites": data,
    })


@login_required
@require_POST
def favorite_toggle(request, recipe_id):
    # TOGGLE: Tambahkan jika belum favorit, hapus jika sudah favorit.
    # Endpoint ini digunakan oleh tombol hati pada katalog resep.
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    favorite = Favorite.objects.filter(
        user=request.user,
        recipe=recipe
    ).first()

    if favorite is not None:
        favorite.delete()

        is_favorited = False
        message = "Resep dihapus dari favorit."

    else:
        favorite, _ = add_favorite(request.user, recipe)

        is_favorited = True
        message = "Resep ditambahkan ke favorit!"

    return JsonResponse({
        "success": True,
        "is_favorited": is_favorited,
        "recipe_id": recipe.pk,
        "message": message,
    })
