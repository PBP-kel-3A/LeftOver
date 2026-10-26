from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from recipes.models import Recipe
from django.utils import timezone

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

    # Mengambil jam saat ulasan di post
    created_at = models.DateTimeField(auto_now_add=True)

    # Mengambil jam saat ulasan di edit
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    # Fungsi untuk hitung waktunya
    def get_time_ago(self):
        now = timezone.now()
        diff = now - self.updated_at
        
        seconds = diff.total_seconds()
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        months = days // 30
        years = days // 365

        if years > 0:
            return f"{int(years)} year{'s' if years > 1 else ''} ago"
        elif months > 0:
            return f"{int(months)} month{'s' if months > 1 else ''} ago"
        elif days > 0:
            return f"{int(days)} day{'s' if days > 1 else ''} ago"
        elif hours > 0:
            return f"{int(hours)} hour{'s' if hours > 1 else ''} ago"
        elif minutes > 0:
            return f"{int(minutes)} minutes ago"
        else:
            return "Just now"


    class Meta:
        ordering = ['-created_at']  # Otomatis urut dari yang paling baru di atas

    def __str__(self):
        return f"{self.user.username} - {self.rating}★ ({self.recipe})"

# Untuk foto yang diupload bisa >1 foto --> maksimal 3 foto saja
class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    # Diubah ke URLField untuk menampung link Cloudinary --> sebelumnya ImageField lokal
    image = models.URLField(max_length=500)

    def __str__(self):
        return f"Foto ulasan oleh {self.review.user.username}"