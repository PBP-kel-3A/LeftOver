from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from recipes.models import Recipe
from reviews.models import Review, ReviewImage
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta

# ==========================================
# 1. TEST: MODELS & LOGIKA WAKTU
# ==========================================
class ReviewModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        # Sesuai model recipes asli, hanya 'name' yang wajib
        self.recipe = Recipe.objects.create(name='Ayam Goreng')
        
        self.review = Review.objects.create(
            recipe=self.recipe,
            user=self.user,
            rating=5,
            comment='Mantap!'
        )
        self.review_image = ReviewImage.objects.create(
            review=self.review,
            image='http://dummy.com/img.jpg'
        )

    def test_review_str_format(self):
        """Memastikan fungsi __str__ di model Review bekerja dengan benar"""
        self.assertEqual(str(self.review), "testuser - 5★ (Ayam Goreng)")

    def test_review_image_str_format(self):
        """Memastikan fungsi __str__ di model ReviewImage bekerja dengan benar"""
        self.assertEqual(str(self.review_image), "Foto ulasan oleh testuser")

    def test_get_time_ago_logic(self):
        """Menguji seluruh percabangan waktu pada fungsi get_time_ago() agar coverage 100%"""
        now = timezone.now()

        # Uji: Just now (< 1 menit)
        self.review.updated_at = now - timedelta(seconds=30)
        self.assertEqual(self.review.get_time_ago(), "Just now")

        # Uji: 1 minute ago (aturan khusus)
        self.review.updated_at = now - timedelta(minutes=1, seconds=5)
        self.assertEqual(self.review.get_time_ago(), "1 minute ago")

        # Uji: > 1 minute ago
        self.review.updated_at = now - timedelta(minutes=5)
        self.assertEqual(self.review.get_time_ago(), "5 minutes ago")

        # Uji: Jam
        self.review.updated_at = now - timedelta(hours=1, minutes=10)
        self.assertEqual(self.review.get_time_ago(), "1 hour ago")
        self.review.updated_at = now - timedelta(hours=3)
        self.assertEqual(self.review.get_time_ago(), "3 hours ago")

        # Uji: Hari
        self.review.updated_at = now - timedelta(days=1, hours=2)
        self.assertEqual(self.review.get_time_ago(), "1 day ago")
        self.review.updated_at = now - timedelta(days=5)
        self.assertEqual(self.review.get_time_ago(), "5 days ago")

        # Uji: Bulan (asumsi 30 hari)
        self.review.updated_at = now - timedelta(days=35)
        self.assertEqual(self.review.get_time_ago(), "1 month ago")
        self.review.updated_at = now - timedelta(days=70)
        self.assertEqual(self.review.get_time_ago(), "2 months ago")

        # Uji: Tahun (asumsi 365 hari)
        self.review.updated_at = now - timedelta(days=400)
        self.assertEqual(self.review.get_time_ago(), "1 year ago")
        self.review.updated_at = now - timedelta(days=800)
        self.assertEqual(self.review.get_time_ago(), "2 years ago")


# ==========================================
# 2. TEST: VIEWS (CRUD & OTORISASI)
# ==========================================
class ReviewViewsTestCase(TestCase):
    def setUp(self):
        self.user_eli = User.objects.create_user(username='eli', password='password123')
        self.user_hacker = User.objects.create_user(username='hacker', password='password123')
        
        # Sekali lagi, gunakan parameter yang valid untuk Recipe
        self.recipe = Recipe.objects.create(name='Nasi Goreng Test')
        
        self.review = Review.objects.create(
            recipe=self.recipe,
            user=self.user_eli,
            rating=4,
            comment='Enak banget!'
        )
        self.client = Client()
        self.mock_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'file_content',
            content_type='image/jpeg'
        )

    def test_add_review_not_logged_in(self):
        url = reverse('reviews:add_review', args=[self.recipe.id])
        response = self.client.post(url, {'rating': 5})
        self.assertEqual(response.status_code, 302)

    def test_add_review_invalid_method(self):
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid method')

    def test_add_review_duplicate(self):
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        response = self.client.post(url, {'rating': 5})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'You have already reviewed this recipe!')

    def test_add_review_invalid_rating(self):
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        response = self.client.post(url, {'rating': 6})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Rating must be between 1 and 5 stars!')

    @patch('cloudinary.uploader.upload')
    def test_add_review_success_with_image(self, mock_cloudinary_upload):
        mock_cloudinary_upload.return_value = {'secure_url': 'http://dummy.com/img.jpg'}
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        
        response = self.client.post(url, {
            'rating': 5,
            'comment': 'Wah mantap!',
            'images': [self.mock_image]
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['avg_rating'], 4.5)
        self.assertEqual(data['review_count'], 2)
        
        new_review = Review.objects.get(user=self.user_hacker)
        self.assertEqual(new_review.images.first().image, 'http://dummy.com/img.jpg')

    def test_edit_review_unauthorized(self):
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:edit_review', args=[self.review.id])
        response = self.client.post(url, {'rating': 5})
        self.assertEqual(response.status_code, 404)

    def test_edit_review_success(self):
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:edit_review', args=[self.review.id])
        response = self.client.post(url, {'rating': 3, 'comment': 'Komen diubah'})
        self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 3)
        self.assertEqual(self.review.comment, 'Komen diubah')
        self.assertTrue(self.review.is_edited)

    def test_delete_review_unauthorized(self):
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:delete_review', args=[self.review.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    @patch('cloudinary.uploader.destroy')
    def test_delete_review_success(self, mock_cloudinary_destroy):
        ReviewImage.objects.create(review=self.review, image='http://res.cloudinary.com/dummy/image.jpg')
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:delete_review', args=[self.review.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['review_count'], 0)
        self.assertEqual(Review.objects.count(), 0)
        mock_cloudinary_destroy.assert_called()

    # ==========================================
    # 3. TEST: COVERAGE TAMBAHAN (EDGE CASES)
    # ==========================================

    def test_invalid_rating_format(self):
        """Menguji _valid_rating dengan input huruf (memicu ValueError)"""
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        response = self.client.post(url, {'rating': 'bukan_angka'})
        self.assertEqual(response.status_code, 400)

    def test_add_review_too_many_images(self):
        """Maksimal 3 gambar saat add_review"""
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        images = [self.mock_image, self.mock_image, self.mock_image, self.mock_image]
        response = self.client.post(url, {'rating': 5, 'images': images})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'You can only upload up to 3 photos!')

    def test_add_review_invalid_image_type(self):
        """Menguji upload file selain gambar (misal TXT/PDF)"""
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        bad_image = SimpleUploadedFile("test.txt", b"isi_teks", content_type="text/plain")
        response = self.client.post(url, {'rating': 5, 'images': [bad_image]})
        self.assertEqual(response.status_code, 400)

    def test_add_review_large_image(self):
        """Menguji upload file berukuran lebih dari 2MB"""
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        # Bikin file bohongan ukuran 2MB lebih sedikit
        large_content = b'0' * (2 * 1024 * 1024 + 10) 
        large_image = SimpleUploadedFile("large.jpg", large_content, content_type="image/jpeg")
        response = self.client.post(url, {'rating': 5, 'images': [large_image]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Each photo must not exceed 2MB in size!')

    @patch('cloudinary.uploader.upload', side_effect=Exception("Cloudinary Error"))
    def test_cloudinary_upload_exception(self, mock_upload):
        """Menguji error handling (try-except) jika server Cloudinary down saat upload"""
        self.client.login(username='hacker', password='password123')
        url = reverse('reviews:add_review', args=[self.recipe.id])
        # Karena kita pasang 'continue' di views saat exception, review akan tetap sukses (200) tanpa foto
        response = self.client.post(url, {'rating': 5, 'images': [self.mock_image]})
        self.assertEqual(response.status_code, 200)

    def test_edit_review_invalid_method(self):
        """Akses GET pada url edit_review harus ditolak"""
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:edit_review', args=[self.review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_delete_review_invalid_method(self):
        """Akses GET pada url delete_review harus ditolak"""
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:delete_review', args=[self.review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    @patch('cloudinary.uploader.upload')
    def test_edit_review_image_logic(self, mock_upload):
        """Menguji logika batasan upload dan penambahan foto baru saat Edit"""
        mock_upload.return_value = {'secure_url': 'http://dummy.com/img2.jpg'}
        self.client.login(username='eli', password='password123')
        url = reverse('reviews:edit_review', args=[self.review.id])
        
        # 1. Edit dan berhasil tambah 2 gambar
        response = self.client.post(url, {'rating': 4, 'images': [self.mock_image, self.mock_image]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.review.images.count(), 2)

        # 2. Coba paksa masukin 2 gambar lagi padahal jatahnya sisa 1 (2 + 2 = 4)
        response = self.client.post(url, {'rating': 4, 'images': [self.mock_image, self.mock_image]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'You can only add 1 more photo(s).')

        # 3. Penuhi jadi 3 gambar
        response = self.client.post(url, {'rating': 4, 'images': [self.mock_image]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.review.images.count(), 3)

        # 4. Kalau sudah 3 gambar, dilarang upload foto baru
        response = self.client.post(url, {'rating': 4, 'images': [self.mock_image]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'This review already has 3 photos. Delete existing photos first to add new ones.')