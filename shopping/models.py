import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import models

from pantry.models import PantryItem

# Satuan yang sering diketik user -> satuan yang ada di PantryItem.Unit
UNIT_ALIASES = {
    "pcs": "pcs", "pc": "pcs", "buah": "pcs", "butir": "pcs", "biji": "pcs",
    "botol": "pcs", "kaleng": "pcs", "papan": "pcs",
    "g": "g", "gr": "g", "gram": "g",
    "kg": "kg", "kilo": "kg",
    "ml": "ml",
    "l": "l", "liter": "l", "lt": "l",
    "siung": "clove", "clove": "clove", "cloves": "clove",
    "batang": "stalk", "stalk": "stalk",
    "ikat": "bunch", "bunch": "bunch",
    "iris": "slice", "slice": "slice", "lembar": "slice",
    "bungkus": "pack", "pack": "pack", "pak": "pack", "sachet": "pack",
}


class ShoppingItem(models.Model):
    """Barang yang perlu dibeli user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_items",
    )
    name = models.CharField(max_length=100)
    # Bebas diisi, misal "1 botol", "500 gr", atau catatan "yang pedas"
    quantity = models.CharField(max_length=50, blank=True, default="")
    is_purchased = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Yang belum dibeli di atas, lalu yang terbaru
        ordering = ["is_purchased", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.quantity})" if self.quantity else self.name

    def pantry_quantity(self):
        """Ubah teks jumlah jadi (angka, satuan) untuk PantryItem.

        "2 botol" -> (2, "pcs"), "500gr" -> (500, "g"), "" -> (1, "pcs")
        """
        match = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]*)", self.quantity)
        if not match:
            return Decimal("1"), PantryItem.Unit.PCS

        try:
            amount = Decimal(match.group(1).replace(",", "."))
        except InvalidOperation:
            amount = Decimal("1")
        if amount <= 0:
            amount = Decimal("1")

        unit = UNIT_ALIASES.get(match.group(2).lower(), PantryItem.Unit.PCS)
        return amount, unit
