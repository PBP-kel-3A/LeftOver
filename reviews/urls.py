from django.urls import path
from . import views

app_name = 'reviews'

# bagian <int:recipe_id> atau <int:review_id> pada file urls.py adalah Path Converter bawaan Django
urlpatterns = [
    path('add/<int:recipe_id>/', views.add_review, name='add_review'),
    path('edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('delete/<int:review_id>/', views.delete_review, name='delete_review'),
]

# Cara kerjanya:
# Yang int: Membatasi nilai di segmen URL tersebut agar hanya menerima angka bulat positif (0, 1, 2, dst). Kalau usernya mengetik huruf kayak /reviews/add/abc/, Django otomatis menolaknya dengan pesan error 404 Not Found tanpa sempat menjalankan fungsi view. Lalu otomatis mengonversi nilai dari string menjadi integer Python. Di dalam parameter fungsi views.py, kita langsung menerima variabel bertipe integer (recipe_id: int) tanpa harus memanggil fungsi int() manual.