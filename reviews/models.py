from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from recipes.models import Recipe
from django.utils import timezone

class Review(models.Model):
    # satu resep bisa punya banyak ulasan (One-to-Many)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='reviews') #kalau resep di hapus, ulasannya ikut dihapus
    user = models.ForeignKey(User, on_delete=models.CASCADE) # pembuat ulasannya
    
    # Default bintangnya 0, tapi nanti wajib diisi minimal 1 dan maksimal 5 saat disimpan/divalidasi
    rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(1), MaxValueValidator(5)] # di cek apakah 1 - 5
    )
    
    # Untuk ulasan teks (opsional)
    comment = models.TextField(blank=True, null=True) # sifatnya optional

    # Mengambil jam saat ulasan di post
    created_at = models.DateTimeField(auto_now_add=True)

    # Mengambil jam saat ulasan di edit
    updated_at = models.DateTimeField(auto_now=True)
    # default di set ke False dulu
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
            if minutes == 1 :
                return f"{int(minutes)} minute ago" # update untuk 1 menit dibuat "minute" (ini kode demo pbp, keep ajaaa)
            else:
                return f"{int(minutes)} minutes ago" # >1 menit
        else:
            return "Just now"


    class Meta:
        ordering = ['-created_at']  # Otomatis urut dari yang paling baru di atas (descending --> ada (-) di awalnya). Menentukan urutan default (bawaan) ketika data diambil dari database melalui QuerySet Django.

    def __str__(self):
        return f"{self.user.username} - {self.rating}★ ({self.recipe})"

# Untuk foto yang diupload bisa >1 foto --> maksimal 3 foto saja
# jadi dipisah jadi model sendiri karena hubungan antara review dan foto itu relasi One-to-Many
class ReviewImage(models.Model):
    # satu review bisa punya beberapa foto
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    # Diubah ke URLField untuk menampung link Cloudinary --> sebelumnya ImageField lokal --> terus ini ga muncul gitu fotonya

    # kalau di deploy ke pws nanti harus upload ulang ulang gitu karena ga muncul lagi
    image = models.URLField(max_length=500)

    def __str__(self):
        return f"Foto ulasan oleh {self.review.user.username}"