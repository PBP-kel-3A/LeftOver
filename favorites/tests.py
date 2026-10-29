
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from recipes.models import Recipe
from .models import Favorite
from reviews.models import Review


User = get_user_model()


class FavoriteTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="testpass123"
        )

        self.recipe = Recipe.objects.create(
            name="Test Chicken",
            category="Chicken",
            instructions="Cook the chicken."
        )

        self.other_recipe = Recipe.objects.create(
            name="Fried Rice",
            category="Rice",
            instructions="Cook the rice."
        )

        self.client.force_login(self.user)

    def create_favorite(self, recipe=None, user=None, note=""):
        return Favorite.objects.create(
            user=user or self.user,
            recipe=recipe or self.recipe,
            personal_note=note
        )

    # ==========================================
    # CREATE
    # ==========================================

    def test_add_favorite(self):
        url = reverse(
            "favorites:favorite_add",
            args=[self.recipe.pk]
        )

        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("favorites:favorite_list")
        )

        self.assertTrue(
            Favorite.objects.filter(
                user=self.user,
                recipe=self.recipe
            ).exists()
        )

    def test_duplicate_favorite_not_created(self):
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

    def test_ajax_add_favorite(self):
        url = reverse(
            "favorites:favorite_add",
            args=[self.recipe.pk]
        )

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertTrue(data["is_favorited"])
        self.assertTrue(data["created"])
        self.assertEqual(data["recipe_id"], self.recipe.pk)
        self.assertIn("favorite_id", data)

    def test_ajax_add_existing_favorite(self):
        self.create_favorite()

        url = reverse(
            "favorites:favorite_add",
            args=[self.recipe.pk]
        )

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])

        self.assertEqual(
            Favorite.objects.filter(
                user=self.user,
                recipe=self.recipe
            ).count(),
            1
        )

    # ==========================================
    # READ & SEARCH
    # ==========================================

    def test_favorite_list(self):
        self.create_favorite()

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.recipe.name)

        self.assertTrue(response.context["has_favorites"])

    def test_favorite_list_only_shows_own_favorites(self):
        self.create_favorite()
        self.create_favorite(
            recipe=self.other_recipe,
            user=self.other_user
        )

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        self.assertContains(response, "Test Chicken")
        self.assertNotContains(response, "Fried Rice")

    def test_search_favorites_case_insensitive(self):
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {"q": "CHICKEN"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chicken")
        self.assertNotContains(response, "Fried Rice")

        self.assertEqual(
            response.context["search_query"],
            "CHICKEN"
        )

    def test_search_query_is_trimmed(self):
        self.create_favorite()

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {"q": "  chicken  "}
        )

        self.assertEqual(
            response.context["search_query"],
            "chicken"
        )

        self.assertEqual(
            response.context["favorites"].count(),
            1
        )

    def test_search_no_results(self):
        self.create_favorite()

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {"q": "Pizza"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["has_favorites"])
        self.assertFalse(response.context["favorites"].exists())

        self.assertContains(response, "No recipes found")

    def test_empty_favorites(self):
        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_favorites"])

        self.assertContains(
            response,
            "No favorite recipes yet"
        )

    def test_filter_favorites_by_category(self):
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {"category": "chicken"}
        )

        self.assertEqual(response.status_code, 200)

        favorites = list(response.context["favorites"])

        self.assertEqual(len(favorites), 1)
        self.assertEqual(favorites[0].recipe, self.recipe)

    def test_category_and_search_together(self):
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {
                "category": "Chicken",
                "q": "Test"
            }
        )

        self.assertEqual(
            response.context["favorites"].count(),
            1
        )

    # ==========================================
    # UPDATE PERSONAL NOTES
    # ==========================================

    def test_update_personal_note(self):
        favorite = self.create_favorite()

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Use less salt."}
        )

        self.assertRedirects(
            response,
            reverse("favorites:favorite_list")
        )

        favorite.refresh_from_db()

        self.assertEqual(
            favorite.personal_note,
            "Use less salt."
        )

    def test_ajax_update_personal_note(self):
        favorite = self.create_favorite()

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Add more chili."},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["personal_note"],
            "Add more chili."
        )

        favorite.refresh_from_db()

        self.assertEqual(
            favorite.personal_note,
            "Add more chili."
        )

    def test_update_personal_note_to_empty(self):
        favorite = self.create_favorite(
            note="Existing note"
        )

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)

        favorite.refresh_from_db()

        self.assertEqual(favorite.personal_note, "")

    def test_user_cannot_update_other_users_favorite(self):
        favorite = self.create_favorite(
            user=self.other_user
        )

        url = reverse(
            "favorites:favorite_update",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            {"personal_note": "Unauthorized note"}
        )

        self.assertEqual(response.status_code, 404)

        favorite.refresh_from_db()
        self.assertEqual(favorite.personal_note, "")

    # ==========================================
    # DELETE
    # ==========================================

    def test_delete_favorite(self):
        favorite = self.create_favorite()

        url = reverse(
            "favorites:favorite_delete",
            args=[favorite.pk]
        )

        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("favorites:favorite_list")
        )

        self.assertFalse(
            Favorite.objects.filter(pk=favorite.pk).exists()
        )

    def test_ajax_delete_favorite(self):
        favorite = self.create_favorite()

        url = reverse(
            "favorites:favorite_delete",
            args=[favorite.pk]
        )

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertFalse(response.json()["is_favorited"])

        self.assertFalse(
            Favorite.objects.filter(pk=favorite.pk).exists()
        )

    def test_user_cannot_delete_other_users_favorite(self):
        favorite = self.create_favorite(
            user=self.other_user
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

    # ==========================================
    # TOGGLE
    # ==========================================

    def test_toggle_favorite(self):
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

    # ==========================================
    # JSON API
    # ==========================================

    def test_favorite_list_json(self):
        self.create_favorite(
            note="My favorite chicken recipe."
        )

        url = reverse("favorites:favorite_list_json")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 1)

        self.assertEqual(
            data["favorites"][0]["recipe_name"],
            "Test Chicken"
        )

        self.assertEqual(
            data["favorites"][0]["personal_note"],
            "My favorite chicken recipe."
        )

    def test_json_category_filter(self):
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        response = self.client.get(
            reverse("favorites:favorite_list_json"),
            {"category": "Rice"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        self.assertEqual(
            response.json()["favorites"][0]["recipe_name"],
            "Fried Rice"
        )

    # ==========================================
    # ACCESS CONTROL & HTTP METHODS
    # ==========================================

    def test_anonymous_user_redirected_from_favorites(self):
        self.client.logout()

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_add_favorite_rejects_get(self):
        response = self.client.get(
            reverse(
                "favorites:favorite_add",
                args=[self.recipe.pk]
            )
        )

        self.assertEqual(response.status_code, 405)

    def test_delete_favorite_rejects_get(self):
        favorite = self.create_favorite()

        response = self.client.get(
            reverse(
                "favorites:favorite_delete",
                args=[favorite.pk]
            )
        )

        self.assertEqual(response.status_code, 405)

        self.assertTrue(
            Favorite.objects.filter(pk=favorite.pk).exists()
        )

    def test_toggle_favorite_rejects_get(self):
        response = self.client.get(
            reverse(
                "favorites:favorite_toggle",
                args=[self.recipe.pk]
            )
        )

        self.assertEqual(response.status_code, 405)



    # ==========================================
    # REVIEW RATINGS
    # ==========================================

    def test_favorite_average_rating(self):
        # Dua review dengan rating 4 dan 5 menghasilkan rata-rata 4.5.
        self.create_favorite()

        Review.objects.create(
            recipe=self.recipe,
            user=self.user,
            rating=4,
            comment="Good recipe."
        )

        Review.objects.create(
            recipe=self.recipe,
            user=self.other_user,
            rating=5,
            comment="Excellent recipe."
        )

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        self.assertEqual(response.status_code, 200)

        favorite = response.context["favorites"].get(
            recipe=self.recipe
        )

        self.assertAlmostEqual(favorite.avg_rating, 4.5)
        self.assertEqual(favorite.review_count, 2)

        # Memastikan rating juga ditampilkan pada halaman.
        self.assertContains(response, "4.5")
        self.assertContains(response, "(2 reviews)")

    def test_favorite_without_reviews(self):
        # Resep tanpa review tidak boleh menghasilkan rating palsu.
        self.create_favorite()

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        favorite = response.context["favorites"].get(
            recipe=self.recipe
        )

        self.assertIsNone(favorite.avg_rating)
        self.assertEqual(favorite.review_count, 0)

        self.assertContains(response, "No reviews yet")

    def test_favorite_rating_is_recipe_specific(self):
        # Rating dari resep berbeda tidak boleh tercampur.
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        Review.objects.create(
            recipe=self.recipe,
            user=self.user,
            rating=5
        )

        Review.objects.create(
            recipe=self.other_recipe,
            user=self.other_user,
            rating=2
        )

        response = self.client.get(
            reverse("favorites:favorite_list")
        )

        favorites = {
            favorite.recipe_id: favorite
            for favorite in response.context["favorites"]
        }

        chicken = favorites[self.recipe.pk]
        rice = favorites[self.other_recipe.pk]

        self.assertAlmostEqual(chicken.avg_rating, 5.0)
        self.assertEqual(chicken.review_count, 1)

        self.assertAlmostEqual(rice.avg_rating, 2.0)
        self.assertEqual(rice.review_count, 1)

    def test_favorite_rating_in_category_filter(self):
        # Annotation rating tetap tersedia setelah filter kategori.
        self.create_favorite(recipe=self.recipe)
        self.create_favorite(recipe=self.other_recipe)

        Review.objects.create(
            recipe=self.recipe,
            user=self.user,
            rating=4
        )

        response = self.client.get(
            reverse("favorites:favorite_list"),
            {"category": "chicken"}
        )

        favorites = list(response.context["favorites"])

        self.assertEqual(len(favorites), 1)
        self.assertEqual(favorites[0].recipe, self.recipe)
        self.assertAlmostEqual(favorites[0].avg_rating, 4.0)
        self.assertEqual(favorites[0].review_count, 1)
