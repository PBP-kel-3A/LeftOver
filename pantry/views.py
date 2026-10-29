from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import PantryItemForm
from .models import PantryItem
from .services import catalog_ingredient_names, resolve_recipe_keywords

LOGIN_URL = "main:login"
EDIT_PREFIX = "edit"

# Chip filter kategori. "Other" sengaja tidak punya chip: bahan dengan
# kategori Other tetap tampil di "All Items".
CATEGORY_CHIPS = [
    (value, label)
    for value, label in PantryItem.Category.choices
    if value != PantryItem.Category.OTHER
]

# Pilihan "Sort by": kode di URL -> (label di UI, argumen order_by).
# Urutan default sama dengan Meta.ordering di model.
SORT_OPTIONS = {
    "expiry": ("Nearest Expiry", ("expiry_date", "name")),
    "expiry_desc": ("Furthest Expiry", ("-expiry_date", "name")),
    "name": ("Name (A-Z)", (Lower("name"), "expiry_date")),
    "recent": ("Recently Added", ("-created_at",)),
}
DEFAULT_SORT = "expiry"


def _list_url(**params):
    """URL halaman pantry + query string; parameter kosong dibuang agar URL tetap bersih."""
    query = urlencode({key: value for key, value in params.items() if value})
    base = reverse("pantry:pantry_list")
    return f"{base}?{query}" if query else base


def _first_error(form):
    """Pesan error pertama dari form, untuk ditampilkan di toast."""
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Invalid data."


@login_required(login_url=LOGIN_URL)
def pantry_list(request):
    """Dashboard pantry + form tambah bahan (Create & Read)."""
    if request.method == "POST":
        form = PantryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, f"{item.name} was added to your pantry.")
            return redirect("pantry:pantry_list")
    else:
        form = PantryItemForm()

    # Seluruh stok milik user. Kartu summary selalu dihitung dari sini,
    # tidak terpengaruh filter kategori yang sedang aktif.
    all_items = PantryItem.objects.filter(user=request.user)

    # Filter kategori lewat ?category=...; nilai yang tidak dikenal -> All Items
    category_labels = dict(CATEGORY_CHIPS)
    active_category = request.GET.get("category", "")
    if active_category not in category_labels:
        active_category = ""

    # Pencarian nama bahan lewat ?q=...
    query = request.GET.get("q", "").strip()[:100]

    # Urutan lewat ?sort=...; nilai yang tidak dikenal -> urutan default
    active_sort = request.GET.get("sort", "")
    if active_sort not in SORT_OPTIONS:
        active_sort = DEFAULT_SORT

    items = all_items
    if active_category:
        items = items.filter(category=active_category)
    if query:
        items = items.filter(name__icontains=query)
    items = items.order_by(*SORT_OPTIONS[active_sort][1])

    # Chip, pencarian, dan urutan saling mempertahankan parameter satu sama lain
    sort_param = "" if active_sort == DEFAULT_SORT else active_sort
    category_chips = [
        {
            "label": label,
            "url": _list_url(category=value, q=query, sort=sort_param),
            "is_active": value == active_category,
        }
        for value, label in CATEGORY_CHIPS
    ]

    context = {
        "form": form,
        "edit_form": PantryItemForm(prefix=EDIT_PREFIX),
        "items": items,
        # Summary: jumlah baris bahan (bukan total kuantitas / nama unik)
        "total_items": all_items.count(),
        "expiring_soon_count": all_items.expiring_soon().count(),
        # Chip filter
        "category_chips": category_chips,
        "all_items_url": _list_url(q=query, sort=sort_param),
        "active_category": active_category,
        "active_category_label": category_labels.get(active_category, ""),
        # Pencarian & urutan
        "query": query,
        "clear_search_url": _list_url(category=active_category, sort=sort_param),
        "sort_options": [(code, label) for code, (label, _) in SORT_OPTIONS.items()],
        "active_sort": active_sort,
        # Saran untuk kolom nama: bahan yang ada di katalog resep
        "catalog_ingredients": catalog_ingredient_names(),
    }
    return render(request, "pantry/pantry_list.html", context)


@login_required(login_url=LOGIN_URL)
@require_POST
def pantry_edit(request, pk):
    """Edit an ingredient, mainly its quantity (Update)."""
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    form = PantryItemForm(request.POST, instance=item, prefix=EDIT_PREFIX)

    if form.is_valid():
        form.save()
        messages.success(request, f"{item.name} was updated.")
    else:
        messages.error(request, f"Couldn't save your changes: {_first_error(form)}")

    return redirect("pantry:pantry_list")


@login_required(login_url=LOGIN_URL)
@require_POST
def pantry_delete(request, pk):
    """Remove an ingredient that was used up or thrown away (Delete)."""
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    name = item.name
    item.delete()
    messages.success(request, f"{name} was removed from your pantry.")
    return redirect("pantry:pantry_list")


@login_required(login_url=LOGIN_URL)
@require_GET
def find_recipes(request):
    """Send the chosen ingredients to the Recipe Catalog's ingredient filter.

    - Some ingredients ticked -> use only those.
    - Nothing ticked -> use every ingredient that hasn't expired.
    Expired ingredients are never searched, and ingredients the catalog
    doesn't recognize are skipped (with a message) so results don't go empty.
    """
    items = PantryItem.objects.filter(
        user=request.user, expiry_date__gte=timezone.localdate()
    )

    selected_ids = [
        int(pk) for pk in request.GET.getlist("items") if pk.isdigit()
    ]
    if selected_ids:
        items = items.filter(pk__in=selected_ids)

    items = list(items)
    if not items:
        messages.warning(
            request,
            "There are no ingredients to search with yet. "
            "Expired ingredients are not included.",
        )
        return redirect("pantry:pantry_list")

    result = resolve_recipe_keywords(items)

    if result.catalog_empty:
        messages.warning(
            request,
            "The recipe catalog is empty, so there is nothing to search yet.",
        )
        return redirect("pantry:pantry_list")

    skipped = ", ".join(result.skipped)
    hint = 'Set a "Recipe Catalog Name" with the edit button to include it.'

    if not result.keywords:
        messages.warning(
            request,
            f"None of these were found in the recipe catalog: {skipped}. {hint}",
        )
        return redirect("pantry:pantry_list")

    if result.skipped:
        # Shown on the Recipe Catalog page after the redirect (see toast.html)
        messages.warning(
            request,
            f"Skipped {skipped}: not found in the recipe catalog. {hint}",
        )

    query = urlencode({"ingredients": ",".join(result.keywords)})
    return redirect(f"{reverse('recipes:recipe_list')}?{query}")
