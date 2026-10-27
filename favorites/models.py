
from django.db import models
from django.conf import settings
from recipes.models import Recipe


class Favorite(models.Model):
    # User yang menyimpan resep
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites"
    )

    # Resep yang difavoritkan
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )

    # Catatan pribadi user (untuk fitur Update)
    personal_note = models.TextField(
        blank=True
    )

    # Waktu resep ditambahkan ke favorit
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_user_favorite"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"
