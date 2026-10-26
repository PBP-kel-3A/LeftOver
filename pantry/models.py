from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class PantryItem(models.Model):
    """A raw ingredient stored in a user's kitchen."""

    # At or below this many days left, an ingredient is "Use Soon" (yellow)
    SOON_THRESHOLD_DAYS = 3

    class Unit(models.TextChoices):
        PCS = "pcs", "pcs"
        GRAM = "g", "g"
        KG = "kg", "kg"
        ML = "ml", "ml"
        LITER = "l", "L"
        CLOVE = "clove", "clove"
        STALK = "stalk", "stalk"
        BUNCH = "bunch", "bunch"
        SLICE = "slice", "slice"
        PACK = "pack", "pack"

    # Shown instead of the label when the quantity is not exactly 1
    UNIT_PLURALS = {
        "clove": "cloves",
        "stalk": "stalks",
        "bunch": "bunches",
        "slice": "slices",
        "pack": "packs",
    }

    class Storage(models.TextChoices):
        CHILLER = "chiller", "Fridge (Chiller)"
        FREEZER = "freezer", "Freezer"
        PANTRY = "pantry", "Room Temp / Shelf"

    class Status(models.TextChoices):
        SAFE = "safe", "Safe"
        SOON = "soon", "Use Soon"
        EXPIRED = "expired", "Urgent / Expired"

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
        max_length=20, choices=Unit.choices, default=Unit.PCS
    )
    storage = models.CharField(
        max_length=20, choices=Storage.choices, default=Storage.CHILLER
    )
    expiry_date = models.DateField()
    # Optional: the ingredient's name in the recipe catalog (e.g. "eggs").
    # When set, it is used as-is by "Find Recipes from Pantry".
    recipe_name = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Closest to expiring first
        ordering = ["expiry_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.quantity_display} {self.unit})"

    # ----- Quantity display -----
    @property
    def quantity_display(self):
        """300.00 -> '300', 2.50 -> '2.5'."""
        return format(self.quantity.normalize(), "f")

    @property
    def unit_display(self):
        """'clove' for 1, 'cloves' for anything else."""
        if self.quantity != 1 and self.unit in self.UNIT_PLURALS:
            return self.UNIT_PLURALS[self.unit]
        return self.get_unit_display()

    # ----- Expiry -----
    @property
    def days_left(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status(self):
        days = self.days_left
        if days <= 0:
            # Already expired, or expiring today -> urgent
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
            return "Today"
        if days <= self.SOON_THRESHOLD_DAYS:
            return f"< {days} Day" if days == 1 else f"< {days} Days"
        return f"{days} days left"


class IngredientAlias(models.Model):
    """Extra wording -> recipe catalog keyword, managed in the Django admin.

    Takes priority over everything else, so it can be used both to add
    missing synonyms (tulsi -> basil) and to override how a name is searched.
    """

    alias = models.CharField(
        max_length=100,
        unique=True,
        help_text="Applies when an ingredient name contains this text, e.g. tulsi",
    )
    keyword = models.CharField(
        max_length=100,
        help_text="Keyword to search in the recipe catalog, e.g. basil",
    )

    class Meta:
        ordering = ["alias"]
        verbose_name = "ingredient alias"
        verbose_name_plural = "ingredient aliases"

    def __str__(self):
        return f"{self.alias} -> {self.keyword}"

    def _normalize(self):
        self.alias = " ".join(self.alias.lower().split())
        self.keyword = " ".join(self.keyword.lower().split())

    def clean(self):
        # Runs before validate_unique, so "Tulsi " and "tulsi" count as duplicates.
        self._normalize()

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)
