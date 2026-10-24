from django.contrib import admin

from .models import PantryItem


@admin.register(PantryItem)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "storage", "expiry_date")
    list_filter = ("storage", "unit")
    search_fields = ("name", "user__username")
