from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

# Rentang waktu (jam) untuk kartu "Expiring Soon" di halaman Pantry
EXPIRING_SOON_HOURS = 48


class PantryItemQuerySet(models.QuerySet):
    def expiring_soon(self, now=None):
        """Bahan yang kedaluwarsa dalam rentang sekarang -> 48 jam ke depan.

        expiry_date hanya berisi tanggal (tanpa jam), jadi bahan dianggap
        masih berlaku sampai akhir hari tersebut (pukul 00:00 hari berikutnya).
        Sebuah bahan dihitung kalau akhir harinya jatuh di antara "sekarang"
        dan "sekarang + 48 jam", berdasarkan waktu lokal:
        - kedaluwarsa kemarin atau lebih lama -> sudah lewat, tidak dihitung
        - kedaluwarsa hari ini                -> dihitung
        - kedaluwarsa besok                   -> dihitung
        - kedaluwarsa lusa atau lebih         -> di luar rentang 48 jam

        `now` boleh diisi (datetime aware) supaya mudah diuji.
        """
        now = timezone.localtime(now)
        batas_akhir = now + timedelta(hours=EXPIRING_SOON_HOURS)

        hari_pertama = now.date()
        # Hari terakhir yang akhir harinya masih <= batas_akhir
        hari_terakhir = (batas_akhir - timedelta(days=1)).date()

        return self.filter(
            expiry_date__gte=hari_pertama, expiry_date__lte=hari_terakhir
        )


class PantryItem(models.Model):
    """Satu bahan mentah yang tersimpan di dapur milik seorang user."""

    # Batas hari untuk status "Use Soon" (pink)
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

    # Dipakai sebagai pengganti label kalau jumlahnya bukan tepat 1
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

    class Category(models.TextChoices):
        VEGETABLES = "vegetables", "Vegetables"
        PROTEIN = "protein", "Protein"
        FRUITS = "fruits", "Fruits"
        SPICES = "spices", "Spices & Seasonings"
        CARBS = "carbs", "Carbohydrates"
        OTHER = "other", "Other"

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
    # Dipilih sendiri oleh user (TheMealDB tidak menyediakan kategori bahan)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
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
    # Opsional: nama bahan di katalog resep (mis. "eggs"). Kalau diisi,
    # dipakai apa adanya oleh "Find recipes from pantry".
    recipe_name = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PantryItemQuerySet.as_manager()

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

    @property
    def unit_display(self):
        """'clove' untuk 1, 'cloves' untuk selain itu."""
        if self.quantity != 1 and self.unit in self.UNIT_PLURALS:
            return self.UNIT_PLURALS[self.unit]
        return self.get_unit_display()

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
    def status_tone(self):
        """Warna pill di tabel: hijau (aman), pink (segera), hitam (sudah lewat).

        Beda dengan `status`: bahan yang kedaluwarsa hari ini masih pink,
        karena belum benar-benar lewat.
        """
        if self.is_expired:
            return "expired"
        if self.days_left <= self.SOON_THRESHOLD_DAYS:
            return "soon"
        return "safe"

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
        if days == 1:
            return "1 day left"
        return f"{days} days left"


class IngredientAlias(models.Model):
    """Tambahan padanan nama bahan -> kata kunci katalog, dikelola di admin.

    Prioritasnya di atas semua tebakan lain, jadi bisa dipakai untuk
    menambah sinonim yang belum ada (tulsi -> basil) atau menimpa cara
    sebuah nama dicari.
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
        # Dipanggil sebelum validate_unique, jadi "Tulsi " dan "tulsi"
        # dianggap duplikat.
        self._normalize()

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)
