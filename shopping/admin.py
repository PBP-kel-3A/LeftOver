from django.contrib import admin

from .models import ShoppingItem


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "is_purchased", "created_at")
    list_filter = ("is_purchased",)
    search_fields = ("name", "user__username")
