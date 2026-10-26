from django.contrib import admin

from recipes.models import RecipeIngredient

from .models import IngredientAlias, PantryItem


@admin.register(PantryItem)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "storage", "expiry_date")
    list_filter = ("storage", "unit")
    search_fields = ("name", "user__username")


@admin.register(IngredientAlias)
class IngredientAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "keyword", "in_catalog")
    search_fields = ("alias", "keyword")

    @admin.display(boolean=True, description="In catalog?")
    def in_catalog(self, obj):
        return RecipeIngredient.objects.filter(
            ingredient__name__icontains=obj.keyword
        ).exists()
