
from django.contrib.auth.models import User
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from unittest.mock import patch
from django.db import IntegrityError

from .models import Recipe, Ingredient, RecipeIngredient
from .forms import RecipeForm



class RecipeAccessTests(TestCase):
    def setUp(self):
        self.recipe = Recipe.objects.create(
            name="Chicken Soup",
            category="Chicken",
            instructions="Boil the chicken until cooked.",
        )

    def test_guest_can_view_recipe_list(self):
        response = self.client.get(reverse("recipes:recipe_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicken Soup")

    def test_guest_can_view_recipe_detail(self):
        response = self.client.get(
            reverse("recipes:recipe_detail", args=[self.recipe.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicken Soup")

    def test_guest_cannot_create_recipe(self):
        response = self.client.post(
            reverse("recipes:recipe_create"),
            {
                "name": "New Recipe",
                "ingredients_text": "Chicken | 200 g",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.filter(name="New Recipe").exists())


class RecipeManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="regular",
            password="testpass123",
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
        )
        self.recipe = Recipe.objects.create(
            name="Chicken Soup",
            category="Chicken",
            instructions="Boil the chicken.",
        )

    def test_regular_user_can_create_recipe(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recipes:recipe_create"),
            {
                "name": "Vegetable Soup",
                "category": "Vegetarian",
                "instructions": "Boil the vegetables.",
                "ingredients_text": (
                    "Carrot | 100 g\n"
                    "Potato | 200 g"
                ),
            },
        )

        self.assertEqual(response.status_code, 302)

        recipe = Recipe.objects.get(name="Vegetable Soup")
        self.assertEqual(recipe.created_by, self.user)
        self.assertIsNone(recipe.mealdb_id)

        self.assertEqual(
            recipe.recipe_ingredients.count(),
            2,
        )

    def test_regular_user_cannot_edit_recipe(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recipes:recipe_update", args=[self.recipe.pk]),
            {
                "name": "Changed Name",
                "ingredients_text": "Chicken | 200 g",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, "Chicken Soup")

    def test_regular_user_cannot_delete_recipe(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recipes:recipe_delete", args=[self.recipe.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Recipe.objects.filter(pk=self.recipe.pk).exists()
        )

    def test_admin_can_edit_recipe(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("recipes:recipe_update", args=[self.recipe.pk]),
            {
                "name": "Updated Chicken Soup",
                "category": "Chicken",
                "instructions": "Cook thoroughly.",
                "ingredients_text": "Chicken | 250 g",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, "Updated Chicken Soup")

    def test_admin_can_delete_recipe(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("recipes:recipe_delete", args=[self.recipe.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Recipe.objects.filter(pk=self.recipe.pk).exists()
        )

    def test_create_rolls_back_when_saving_ingredients_fails(self):
        self.client.force_login(self.user)

        with patch(
            "recipes.views.save_recipe_ingredients",
            side_effect=IntegrityError("Simulated database failure"),
        ):
            with self.assertRaises(IntegrityError):
                self.client.post(
                    reverse("recipes:recipe_create"),
                    {
                        "name": "Transaction Test Recipe",
                        "category": "Test",
                        "instructions": "Test instructions",
                        "ingredients_text": "Chicken | 200 g",
                    },
                )

        self.assertFalse(
            Recipe.objects.filter(name="Transaction Test Recipe").exists()
        )

    def test_delete_rejects_post_without_csrf_token(self):
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)

        response = csrf_client.post(
            reverse(
                "recipes:recipe_delete",
                args=[self.recipe.pk],
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Recipe.objects.filter(pk=self.recipe.pk).exists()
        )

    def test_admin_edit_replaces_recipe_ingredients(self):
        self.client.force_login(self.admin)

        old_ingredient = Ingredient.objects.create(name="Old Ingredient")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=old_ingredient,
            measure="100 g",
        )

        response = self.client.post(
            reverse("recipes:recipe_update", args=[self.recipe.pk]),
            {
                "name": "Chicken Soup",
                "category": "Chicken",
                "instructions": "Cook thoroughly.",
                "ingredients_text": "New Ingredient | 200 g",
            },
        )

        self.assertEqual(response.status_code, 302)

        recipe_ingredients = RecipeIngredient.objects.filter(
            recipe=self.recipe
        ).select_related("ingredient")

        self.assertEqual(recipe_ingredients.count(), 1)
        self.assertEqual(
            recipe_ingredients.first().ingredient.name,
            "New Ingredient",
        )
        self.assertEqual(
            recipe_ingredients.first().measure,
            "200 g",
        )

class RecipeIngredientValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cook",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_create_rejects_invalid_ingredient_format(self):
        response = self.client.post(
            reverse("recipes:recipe_create"),
            {
                "name": "Invalid Soup",
                "ingredients_text": "Chicken without measure separator",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Recipe.objects.filter(name="Invalid Soup").exists()
        )
        self.assertFalse(RecipeIngredient.objects.exists())

    def test_create_rejects_duplicate_ingredients(self):
        response = self.client.post(
            reverse("recipes:recipe_create"),
            {
                "name": "Duplicate Soup",
                "ingredients_text": (
                    "Chicken | 200 g\n"
                    "chicken | 300 g"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Recipe.objects.filter(name="Duplicate Soup").exists()
        )
        self.assertFalse(RecipeIngredient.objects.exists())

    def test_create_rejects_ingredients_text_over_limit(self):
        response = self.client.post(
            reverse("recipes:recipe_create"),
            {
                "name": "Oversized Recipe",
                "ingredients_text": "x" * 10001,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Recipe.objects.filter(name="Oversized Recipe").exists()
        )
        self.assertFalse(RecipeIngredient.objects.exists())

class RecipeFormURLTests(SimpleTestCase):
    def test_accepts_valid_youtube_url(self):
        form = RecipeForm(data={
            "name": "Test Recipe",
            "youtube_url": "https://www.youtube.com/watch?v=abc123",
            "ingredients_text": "Chicken | 200 g",
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_non_youtube_domain(self):
        form = RecipeForm(data={
            "name": "Test Recipe",
            "youtube_url": "https://example.com/video",
            "ingredients_text": "Chicken | 200 g",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("youtube_url", form.errors)

    def test_rejects_lookalike_youtube_domain(self):
        form = RecipeForm(data={
            "name": "Test Recipe",
            "youtube_url": "https://youtube.com.example.org/video",
            "ingredients_text": "Chicken | 200 g",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("youtube_url", form.errors)
