from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import PantryItemForm
from .models import PantryItem
from .services import catalog_ingredient_names, resolve_recipe_keywords

LOGIN_URL = "main:login"
EDIT_PREFIX = "edit"


def _first_error(form):
    """First error message of a form, for showing in a toast."""
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Invalid data."


@login_required(login_url=LOGIN_URL)
def pantry_list(request):
    """Pantry dashboard + add form (Create & Read)."""
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

    context = {
        "form": form,
        "edit_form": PantryItemForm(prefix=EDIT_PREFIX),
        "items": PantryItem.objects.filter(user=request.user),
        # Suggestions for the name fields: ingredients that exist in the catalog
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
