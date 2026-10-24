from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .forms import PantryItemForm
from .models import PantryItem
from .services import recipe_keywords

LOGIN_URL = "main:login"
EDIT_PREFIX = "edit"


def _first_error(form):
    """Ambil pesan error pertama dari form untuk ditampilkan di toast."""
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Data tidak valid."


@login_required(login_url=LOGIN_URL)
def pantry_list(request):
    """Dashboard stok dapur + form tambah bahan (Create & Read)."""
    if request.method == "POST":
        form = PantryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(
                request, f"{item.name} berhasil disimpan ke stok dapur."
            )
            return redirect("pantry:pantry_list")
    else:
        form = PantryItemForm()

    context = {
        "form": form,
        "edit_form": PantryItemForm(prefix=EDIT_PREFIX),
        "items": PantryItem.objects.filter(user=request.user),
    }
    return render(request, "pantry/pantry_list.html", context)


@login_required(login_url=LOGIN_URL)
@require_POST
def pantry_edit(request, pk):
    """Ubah data bahan, terutama jumlah stok (Update)."""
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    form = PantryItemForm(request.POST, instance=item, prefix=EDIT_PREFIX)

    if form.is_valid():
        form.save()
        messages.success(request, f"Stok {item.name} berhasil diperbarui.")
    else:
        messages.error(request, f"Gagal menyimpan perubahan: {_first_error(form)}")

    return redirect("pantry:pantry_list")


@login_required(login_url=LOGIN_URL)
@require_POST
def pantry_delete(request, pk):
    """Hapus bahan yang sudah terpakai / dibuang (Delete)."""
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    name = item.name
    item.delete()
    messages.success(request, f"{name} dihapus dari stok dapur.")
    return redirect("pantry:pantry_list")


@login_required(login_url=LOGIN_URL)
@require_GET
def find_recipes(request):
    """Kirim bahan terpilih ke filter bahan di Katalog Resep.

    - Ada bahan yang dicentang -> pakai bahan itu saja.
    - Tidak ada yang dicentang -> pakai semua bahan yang belum expired.
    Bahan yang sudah expired tidak pernah ikut dicari.
    """
    items = PantryItem.objects.filter(
        user=request.user, expiry_date__gte=timezone.localdate()
    )

    selected_ids = [
        int(pk) for pk in request.GET.getlist("items") if pk.isdigit()
    ]
    if selected_ids:
        items = items.filter(pk__in=selected_ids)

    keywords = recipe_keywords(items)
    if not keywords:
        messages.warning(
            request,
            "Belum ada bahan yang bisa dipakai untuk mencari resep. "
            "Bahan yang sudah expired tidak disertakan.",
        )
        return redirect("pantry:pantry_list")

    query = urlencode({"ingredients": ",".join(keywords)})
    return redirect(f"{reverse('recipes:recipe_list')}?{query}")
