from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from recipes.models import Ingredient, Recipe, RecipeIngredient

from .models import PantryItem
from .services import recipe_keywords, to_recipe_keyword


def make_item(user, name="Telur Ayam", days=5, **kwargs):
    defaults = {"quantity": Decimal("4"), "unit": "butir"}
    defaults.update(kwargs)
    return PantryItem.objects.create(
        user=user,
        name=name,
        expiry_date=timezone.localdate() + timedelta(days=days),
        **defaults,
    )


class StatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")

    def test_status_colors_and_labels(self):
        cases = [
            (10, "safe", "10 Hari lagi"),
            (4, "safe", "4 Hari lagi"),
            (3, "soon", "< 3 Hari"),
            (1, "soon", "< 1 Hari"),
            (0, "expired", "Hari ini"),
            (-1, "expired", "Expired"),
        ]
        for days, status, label in cases:
            with self.subTest(days=days):
                item = make_item(self.user, days=days)
                self.assertEqual(item.status, status)
                self.assertEqual(item.status_label, label)

    def test_quantity_display_drops_trailing_zeros(self):
        item = make_item(self.user, quantity=Decimal("300.00"), unit="gram")
        item.refresh_from_db()
        self.assertEqual(item.quantity_display, "300")
        item.quantity = Decimal("2.50")
        self.assertEqual(item.quantity_display, "2.5")


class KeywordTests(TestCase):
    def test_indonesian_names_are_translated(self):
        cases = {
            "Telur Ayam": "egg",          # "telur" menang atas "ayam"
            "Daging Ayam": "chicken",
            "Wortel Segar": "carrot",
            "Bawang Putih": "garlic",     # bukan "onion"
            "Bawang Merah": "onion",
            "Daun Bawang": "spring onion",
            "Kubis": "cabbage",           # bukan "ubi" (sweet potato)
            "Jeruk Nipis": "lime",
            "Tomato": "tomato",           # sudah bahasa Inggris -> apa adanya
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(to_recipe_keyword(name), expected)

    def test_keywords_are_unique(self):
        user = User.objects.create_user("u", password="pw12345!")
        items = [make_item(user, "Bawang Merah"), make_item(user, "Bawang Bombay")]
        self.assertEqual(recipe_keywords(items), ["onion"])


class PantryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")
        self.other = User.objects.create_user("lain", password="pw12345!")
        self.client.login(username="rahmi", password="pw12345!")
        self.list_url = reverse("pantry:pantry_list")

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertRedirects(
            response, f"{reverse('main:login')}?next={self.list_url}"
        )

    def test_only_own_items_are_listed(self):
        make_item(self.user, "Wortel Segar")
        make_item(self.other, "Susu UHT")
        response = self.client.get(self.list_url)
        self.assertContains(response, "Wortel Segar")
        self.assertNotContains(response, "Susu UHT")

    def test_create(self):
        expiry = timezone.localdate() + timedelta(days=7)
        response = self.client.post(self.list_url, {
            "name": "  Daging   Ayam ",
            "quantity": "500",
            "unit": "gram",
            "expiry_date": expiry.isoformat(),
            "storage": "freezer",
        })
        self.assertRedirects(response, self.list_url)
        item = PantryItem.objects.get()
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, "Daging Ayam")
        self.assertEqual(item.quantity, Decimal("500"))
        self.assertEqual(item.storage, "freezer")

    def test_create_invalid_shows_errors_and_saves_nothing(self):
        response = self.client.post(self.list_url, {
            "name": "", "quantity": "-1", "unit": "gram",
            "expiry_date": "", "storage": "freezer",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PantryItem.objects.count(), 0)
        self.assertContains(response, "Nama bahan wajib diisi.")
        self.assertContains(response, "Jumlah harus lebih dari 0.")
        self.assertContains(response, "Tanggal kedaluwarsa wajib diisi.")

    def test_edit_quantity(self):
        item = make_item(self.user, quantity=Decimal("4"))
        response = self.client.post(
            reverse("pantry:pantry_edit", args=[item.pk]),
            {
                "edit-name": item.name,
                "edit-quantity": "2",
                "edit-unit": "butir",
                "edit-expiry_date": item.expiry_date.isoformat(),
                "edit-storage": "chiller",
            },
        )
        self.assertRedirects(response, self.list_url)
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("2"))

    def test_cannot_edit_or_delete_other_users_item(self):
        item = make_item(self.other)
        self.assertEqual(
            self.client.post(reverse("pantry:pantry_delete", args=[item.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("pantry:pantry_edit", args=[item.pk]), {}).status_code,
            404,
        )
        self.assertTrue(PantryItem.objects.filter(pk=item.pk).exists())

    def test_delete(self):
        item = make_item(self.user)
        self.client.post(reverse("pantry:pantry_delete", args=[item.pk]))
        self.assertFalse(PantryItem.objects.filter(pk=item.pk).exists())

    def test_delete_requires_post(self):
        item = make_item(self.user)
        response = self.client.get(reverse("pantry:pantry_delete", args=[item.pk]))
        self.assertEqual(response.status_code, 405)


class FindRecipesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")
        self.client.login(username="rahmi", password="pw12345!")
        self.url = reverse("pantry:find_recipes")
        self.recipes_url = reverse("recipes:recipe_list")

    def test_selected_items_only(self):
        egg = make_item(self.user, "Telur Ayam", days=2)
        make_item(self.user, "Wortel Segar", days=1)
        response = self.client.get(self.url, {"items": [egg.pk]})
        self.assertRedirects(
            response, f"{self.recipes_url}?ingredients=egg",
            fetch_redirect_response=False,
        )

    def test_no_selection_uses_all_non_expired(self):
        make_item(self.user, "Telur Ayam", days=2)
        make_item(self.user, "Wortel Segar", days=1)
        make_item(self.user, "Daging Ayam", days=-1)  # expired -> dilewati
        response = self.client.get(self.url)
        # urut dari yang paling cepat kedaluwarsa
        self.assertRedirects(
            response, f"{self.recipes_url}?ingredients=carrot%2Cegg",
            fetch_redirect_response=False,
        )

    def test_expired_item_is_never_searched_even_if_selected(self):
        old = make_item(self.user, "Daging Ayam", days=-1)
        response = self.client.get(self.url, {"items": [old.pk]})
        self.assertRedirects(response, reverse("pantry:pantry_list"))

    def test_other_users_items_are_ignored(self):
        other = User.objects.create_user("lain", password="pw12345!")
        theirs = make_item(other, "Susu UHT")
        response = self.client.get(self.url, {"items": [theirs.pk]})
        self.assertRedirects(response, reverse("pantry:pantry_list"))

    def test_catalog_actually_filters_by_the_redirect(self):
        egg = Ingredient.objects.create(name="Eggs")
        omelette = Recipe.objects.create(mealdb_id="1", name="Omelette")
        RecipeIngredient.objects.create(recipe=omelette, ingredient=egg)
        Recipe.objects.create(mealdb_id="2", name="Plain Rice")

        item = make_item(self.user, "Telur Ayam")
        response = self.client.get(self.url, {"items": [item.pk]}, follow=True)
        self.assertContains(response, "Omelette")
        self.assertNotContains(response, "Plain Rice")
