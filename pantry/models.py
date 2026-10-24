from django.db import models
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class PantryItem(models.Model):
    # Batas hari untuk status kuning ("Segera Olah")
    SOON_THRESHOLD_DAYS = 3

    class Unit(models.TextChoices):
        BUTIR = "butir", "butir"
        BUAH = "buah", "buah"
        GRAM = "gram", "gram"
        KG = "kg", "kg"
        ML = "ml", "ml"
        LITER = "liter", "liter"
        BATANG = "batang", "batang"
        SIUNG = "siung", "siung"
        IKAT = "ikat", "ikat"
        LEMBAR = "lembar", "lembar"
        BUNGKUS = "bungkus", "bungkus"

    class Storage(models.TextChoices):
        CHILLER = "chiller", "Kulkas (Chiller)"
        FREEZER = "freezer", "Freezer"
        PANTRY = "pantry", "Suhu Ruang / Rak"

    class Status(models.TextChoices):
        SAFE = "safe", "Aman"
        SOON = "soon", "Segera Olah"
        EXPIRED = "expired", "Mendesak / Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pantry_items",
    )
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit = models.CharField(
        max_length=20, choices=Unit.choices, default=Unit.BUTIR
    )
    storage = models.CharField(
        max_length=20, choices=Storage.choices, default=Storage.CHILLER
    )
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Yang paling cepat kedaluwarsa tampil paling atas
        ordering = ["expiry_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.quantity_display} {self.unit})"

    # ----- Tampilan jumlah -----
    @property
    def quantity_display(self):
        """300.00 -> '300', 2.50 -> '2.5'."""
        return format(self.quantity.normalize(), "f")

    # ----- Kedaluwarsa -----
    @property
    def days_left(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status(self):
        days = self.days_left
        if days <= 0:
            # Sudah lewat atau kedaluwarsa hari ini -> mendesak
            return self.Status.EXPIRED
        if days <= self.SOON_THRESHOLD_DAYS:
            return self.Status.SOON
        return self.Status.SAFE

    @property
    def is_expired(self):
        return self.days_left < 0

    @property
    def status_label(self):
        days = self.days_left
        if days < 0:
            return "Expired"
        if days == 0:
            return "Hari ini"
        if days <= self.SOON_THRESHOLD_DAYS:
            return f"< {days} Hari"
        return f"{days} Hari lagi"
