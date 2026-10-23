from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from recipes.models import Recipe

class Review(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Default bintangnya 0, tapi nanti wajib diisi minimal 1 dan maksimal 5 saat disimpan/divalidasi
    rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Untuk ulasan teks (opsional)
    comment = models.TextField(blank=True, null=True)
    
    # Untuk foto masakan by usernya (opsional)
    image = models.ImageField(upload_to='review_images/', blank=True, null=True)

    # Mengambil jam saat ulasan di post
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Otomatis urut dari yang paling baru di atas

    def __str__(self):
        return f"{self.user.username} - {self.rating}★ ({self.recipe})"