
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from recipes.models import Recipe
from .models import Favorite


User = get_user_model()


class FavoriteTests(TestCase):

    def setUp(self):
        # Membuat dua user untuk menguji kepemilikan data
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="testpass123"
        )

        # Membuat resep untuk pengujian
        self.recipe = Recipe.objects.create(
            name="Test Chicken",
            category="Chicken",
            instructions="Cook the chicken."
        )

        # Login sebagai user pertama
        self.client.force_login(self.user)

    def test_add_favorite(self):
        # CREATE: user dapat menambahkan resep ke Favorites
        url = reverse(
            "favorites:favorite_add",
            args=[self.recipe.pk]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Favorite.objects.filter(
                user=self.user,
                recipe=self.recipe
            ).exists()
        )

    def test_duplicate_favorite_not_created(self):
        # Resep yang sama tidak boleh tersimpan dua kali oleh user yang sama
        url = reverse(
            "favorites:favorite_add",
            args=[self.recipe.pk]
        )

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(
            Favorite.objects.filter(
                user=self.user,
                recipe=self.recipe
            ).count(),
            1
        )

    def test_favorite_list(self):
        # READ: halaman menampilkan favorit milik user
        favorite = Favorite.objects.create(
            user=self.user,
            recipe=self.recipe
        )

        url = reverse("favorites:favorite_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, favorite.recipe.name)

    def test_update_personal_note(self):
        # UPDATE: user dapat mengubah catatan pribadinya
        favorite = Favorite.objects.create(
            user=self.user,
            recipe=self.recipe
        )

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Kurangi garam"}
        )

        self.assertEqual(response.status_code, 302)

        favorite.refresh_from_db()

        self.assertEqual(
            favorite.personal_note,
            "Kurangi garam"
        )

    def test_delete_favorite(self):
        # DELETE: user dapat menghapus favorit miliknya
        favorite = Favorite.objects.create(
            user=self.user,
            recipe=self.recipe
        )

        url = reverse(
            "favorites:favorite_delete",
            args=[favorite.pk]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Favorite.objects.filter(pk=favorite.pk).exists()
        )

    def test_user_cannot_update_other_users_favorite(self):
        # User tidak boleh mengedit favorit milik user lain
        favorite = Favorite.objects.create(
            user=self.other_user,
            recipe=self.recipe
        )

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Catatan ilegal"}
        )

        self.assertEqual(response.status_code, 404)

        favorite.refresh_from_db()
        self.assertEqual(favorite.personal_note, "")

    def test_user_cannot_delete_other_users_favorite(self):
        # User tidak boleh menghapus favorit milik user lain
        favorite = Favorite.objects.create(
            user=self.other_user,
            recipe=self.recipe
        )

        url = reverse(
            "favorites:favorite_delete",
            args=[favorite.pk]
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Favorite.objects.filter(pk=favorite.pk).exists()
        )

    def test_toggle_favorite(self):
        # Toggle pertama menambahkan favorit
        url = reverse(
            "favorites:favorite_toggle",
            args=[self.recipe.pk]
        )

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_favorited"])

        # Toggle kedua menghapus favorit
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_favorited"])

        self.assertFalse(
            Favorite.objects.filter(
                user=self.user,
                recipe=self.recipe
            ).exists()
        )

    def test_ajax_update_personal_note(self):
        # Menguji response JSON yang digunakan modal Edit
        favorite = Favorite.objects.create(
            user=self.user,
            recipe=self.recipe
        )

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Tambahkan cabai"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        favorite.refresh_from_db()

        self.assertEqual(
            favorite.personal_note,
            "Tambahkan cabai"
        )
