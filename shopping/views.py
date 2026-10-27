from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import ShoppingItemForm
from .models import ShoppingItem

LOGIN_URL = "main:login"


def _first_error(form):
    """Pesan error pertama dari form, untuk ditampilkan di toast."""
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Data tidak valid."


@login_required(login_url=LOGIN_URL)
def shopping_list(request):
    """Halaman daftar belanja (Read)."""
    items = ShoppingItem.objects.filter(user=request.user)
    purchased = sum(1 for item in items if item.is_purchased)

    context = {
        "form": ShoppingItemForm(),
        "items": items,
        "total_count": len(items),
        "pending_count": len(items) - purchased,
        "purchased_count": purchased,
    }
    return render(request, "shopping/shopping_list.html", context)


# Semua endpoint di bawah dipanggil lewat AJAX dan mengembalikan JSON.

@login_required(login_url=LOGIN_URL)
@require_POST
def shopping_add(request):
    """Tambah barang ke daftar belanja (Create)."""
    form = ShoppingItemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"success": False, "error": _first_error(form)}, status=400)

    item = form.save(commit=False)
    item.user = request.user
    item.save()

    # Kirim potongan HTML supaya JS bisa langsung menampilkan barang baru
    html = render_to_string("shopping/_shopping_item.html", {"item": item}, request=request)
    return JsonResponse({"success": True, "html": html, "name": item.name})


@login_required(login_url=LOGIN_URL)
@require_POST
def shopping_toggle(request, pk):
    """Centang / batal centang 'Sudah Dibeli' (Update)."""
    # user=request.user supaya user tidak bisa mengubah barang orang lain
    item = get_object_or_404(ShoppingItem, pk=pk, user=request.user)
    item.is_purchased = not item.is_purchased
    item.save(update_fields=["is_purchased", "updated_at"])
    return JsonResponse({"success": True, "is_purchased": item.is_purchased})


@login_required(login_url=LOGIN_URL)
@require_POST
def shopping_delete(request, pk):
    """Hapus barang dari daftar belanja (Delete)."""
    item = get_object_or_404(ShoppingItem, pk=pk, user=request.user)
    name = item.name
    item.delete()
    return JsonResponse({"success": True, "name": name})
