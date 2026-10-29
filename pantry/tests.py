import importlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from recipes.models import Ingredient, Recipe, RecipeIngredient

from .forms import PantryItemForm
from .models import IngredientAlias, PantryItem
from .services import apply_synonyms, resolve_recipe_keywords

JAKARTA = ZoneInfo("Asia/Jakarta")


def make_item(user, name="Eggs", days=5, **kwargs):
    defaults = {"quantity": Decimal("4"), "unit": "pcs"}
    defaults.update(kwargs)
    return PantryItem.objects.create(
        user=user,
        name=name,
        expiry_date=timezone.localdate() + timedelta(days=days),
        **defaults,
    )


def make_catalog(*ingredient_names):
    """Satu resep contoh yang memakai semua bahan yang diberikan."""
    recipe = Recipe.objects.create(mealdb_id="test-1", name="Test Dish")
    for name in ingredient_names:
        ingredient = Ingredient.objects.create(name=name)
        RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient)
    return recipe


def catalog_url(recipes_url, keywords):
    return f"{recipes_url}?{urlencode({'ingredients': keywords})}"


class ModelDisplayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")

    def test_status_labels_and_tones(self):
        # (sisa hari, status lama, warna pill, label)
        cases = [
            (10, "safe", "safe", "10 days left"),
            (4, "safe", "safe", "4 days left"),
            (3, "soon", "soon", "3 days left"),
            (1, "soon", "soon", "1 day left"),
            (0, "expired", "soon", "Today"),      # hari ini: pill pink, belum hitam
            (-1, "expired", "expired", "Expired"),
        ]
        for days, status, tone, label in cases:
            with self.subTest(days=days):
                item = make_item(self.user, days=days)
                self.assertEqual(item.status, status)
                self.assertEqual(item.status_tone, tone)
                self.assertEqual(item.status_label, label)

    def test_quantity_display_drops_trailing_zeros(self):
        item = make_item(self.user, quantity=Decimal("300.00"), unit="g")
        item.refresh_from_db()
        self.assertEqual(item.quantity_display, "300")
        item.quantity = Decimal("2.50")
        self.assertEqual(item.quantity_display, "2.5")

    def test_unit_is_pluralized_only_when_needed(self):
        clove = make_item(self.user, "Garlic", quantity=Decimal("1"), unit="clove")
        self.assertEqual(clove.unit_display, "clove")
        clove.quantity = Decimal("8")
        self.assertEqual(clove.unit_display, "cloves")
        clove.unit = "pcs"
        self.assertEqual(clove.unit_display, "pcs")
        clove.unit = "l"
        self.assertEqual(clove.unit_display, "L")

    def test_category_defaults_to_other(self):
        self.assertEqual(make_item(self.user).category, "other")


class ExpiringSoonTests(TestCase):
    """Rentang 48 jam: dari sekarang sampai 48 jam ke depan (waktu lokal)."""

    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")
        self.today = date(2026, 10, 28)

    def add(self, name, offset_days):
        return PantryItem.objects.create(
            user=self.user,
            name=name,
            quantity=Decimal("1"),
            expiry_date=self.today + timedelta(days=offset_days),
        )

    def names(self, now):
        qs = PantryItem.objects.filter(user=self.user).expiring_soon(now=now)
        return sorted(item.name for item in qs)

    def test_today_and_tomorrow_are_counted_but_not_past_or_later(self):
        self.add("Expired last week", -7)
        self.add("Expired yesterday", -1)
        self.add("Today A", 0)
        self.add("Today B", 0)
        self.add("Tomorrow", 1)
        self.add("In two days", 2)
        self.add("Next week", 7)

        # Hasilnya sama kapan pun di hari yang sama (pagi, siang, hampir tengah malam)
        for jam, menit in [(0, 0), (0, 5), (12, 30), (23, 59)]:
            with self.subTest(jam=jam, menit=menit):
                now = datetime(2026, 10, 28, jam, menit, tzinfo=JAKARTA)
                self.assertEqual(
                    self.names(now), ["Today A", "Today B", "Tomorrow"]
                )

    def test_window_follows_local_time_not_utc(self):
        # 28 Okt 06:00 WIB = 27 Okt 23:00 UTC. Hari lokalnya tetap 28 Okt.
        self.add("Expired yesterday", -1)
        self.add("Today", 0)
        now_utc = datetime(2026, 10, 27, 23, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(self.names(now_utc), ["Today"])

    def test_nothing_to_count(self):
        self.add("Next week", 7)
        self.assertEqual(self.names(datetime(2026, 10, 28, 9, 0, tzinfo=JAKARTA)), [])


class CategoryFormTests(TestCase):
    def valid_data(self, **extra):
        data = {
            "name": "Spinach",
            "quantity": "1",
            "unit": "bunch",
            "expiry_date": "2026-11-01",
            "storage": "chiller",
        }
        data.update(extra)
        return data

    def test_category_choices_are_english(self):
        labels = [label for _, label in PantryItem.Category.choices]
        self.assertEqual(
            labels,
            ["Vegetables", "Protein", "Fruits", "Spices & Seasonings",
             "Carbohydrates", "Other"],
        )

    def test_missing_category_becomes_other_for_new_item(self):
        form = PantryItemForm(self.valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["category"], "other")

    def test_missing_category_keeps_old_category_when_editing(self):
        user = User.objects.create_user("rahmi", password="pw12345!")
        item = make_item(user, "Spinach", category="vegetables")
        form = PantryItemForm(self.valid_data(), instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().category, "vegetables")

    def test_unknown_category_is_rejected(self):
        form = PantryItemForm(self.valid_data(category="dairy"))
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)


class UnitMigrationTests(TestCase):
    """0003 mengonversi satuan lama (butir, siung, ...) ke English."""

    def test_existing_rows_are_converted_both_ways(self):
        migration = importlib.import_module("pantry.migrations.0003_english_ui")
        user = User.objects.create_user("rahmi", password="pw12345!")
        legacy = {
            "butir": "pcs", "buah": "pcs", "gram": "g", "kg": "kg",
            "liter": "l", "siung": "clove", "batang": "stalk",
            "ikat": "bunch", "lembar": "slice", "bungkus": "pack",
        }
        items = {old: make_item(user, f"Item {old}", unit=old) for old in legacy}

        migration.units_to_english(apps, None)
        for old, new in legacy.items():
            items[old].refresh_from_db()
            self.assertEqual(items[old].unit, new, old)

        migration.units_to_indonesian(apps, None)
        items["siung"].refresh_from_db()
        items["gram"].refresh_from_db()
        self.assertEqual(items["siung"].unit, "siung")
        self.assertEqual(items["gram"].unit, "gram")


class SynonymTests(TestCase):
    def test_synonyms_are_applied_inside_the_name(self):
        cases = {
            "Eggplant": "aubergine",
            "Zucchinis": "courgette",                # bentuk jamak ikut cocok
            "Scallions": "spring onion",
            "Green Onion": "spring onion",
            "Chili Powder": "chilli powder",         # sisa nama dipertahankan
            "Heavy Whipping Cream": "double cream",  # frasa lebih panjang menang
            "Carrots": "carrots",                    # tanpa sinonim -> tetap
            "  Fresh   Eggs ": "fresh eggs",         # spasi dirapikan
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(apply_synonyms(name), expected)


class IngredientAliasTests(TestCase):
    def test_alias_is_normalized_on_save(self):
        alias = IngredientAlias.objects.create(alias="  Tulsi ", keyword=" Holy  Basil")
        self.assertEqual(alias.alias, "tulsi")
        self.assertEqual(alias.keyword, "holy basil")

    def test_duplicate_alias_ignoring_case_is_rejected(self):
        IngredientAlias.objects.create(alias="tulsi", keyword="basil")
        duplicate = IngredientAlias(alias="  TULSI ", keyword="other")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class ResolveKeywordsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")

    def keywords(self, *names, **item_kwargs):
        items = [make_item(self.user, name, **item_kwargs) for name in names]
        return resolve_recipe_keywords(items)

    def test_name_as_typed_is_used_when_the_catalog_has_it(self):
        make_catalog("Eggs", "Carrots")
        self.assertEqual(self.keywords("Eggs", "Carrots").keywords, ["eggs", "carrots"])

    def test_matching_ignores_case_and_extra_spaces(self):
        make_catalog("Spring Onions")
        self.assertEqual(self.keywords("  SPRING   onions ").keywords, ["spring onions"])

    def test_singular_matches_plural_catalog_name_and_vice_versa(self):
        make_catalog("Eggs", "Chicken")
        result = self.keywords("Egg", "Chickens")
        self.assertEqual(result.keywords, ["egg", "chicken"])

    def test_same_ingredient_twice_is_sent_once(self):
        make_catalog("Eggs")
        self.assertEqual(self.keywords("Eggs", "eggs").keywords, ["eggs"])

    def test_unknown_ingredient_is_skipped_but_others_still_work(self):
        make_catalog("Eggs")
        result = self.keywords("Eggs", "Dragonfruit")
        self.assertEqual(result.keywords, ["eggs"])
        self.assertEqual(result.skipped, ["Dragonfruit"])

    def test_empty_catalog_skips_everything(self):
        result = self.keywords("Eggs")
        self.assertTrue(result.catalog_empty)
        self.assertEqual(result.keywords, [])
        self.assertEqual(result.skipped, ["Eggs"])

    def test_non_english_name_is_skipped_not_silently_wrong(self):
        make_catalog("Eggs")
        result = self.keywords("Telur")
        self.assertEqual(result.keywords, [])
        self.assertEqual(result.skipped, ["Telur"])

    def test_builtin_synonym_is_used_when_the_name_is_not_in_the_catalog(self):
        make_catalog("Aubergine")
        self.assertEqual(self.keywords("Eggplant").keywords, ["aubergine"])

    def test_name_as_typed_beats_builtin_synonym(self):
        make_catalog("Shrimp", "Prawns")
        self.assertEqual(self.keywords("Shrimp").keywords, ["shrimp"])

    def test_database_alias_covers_missing_wording(self):
        make_catalog("Basil")
        IngredientAlias.objects.create(alias="tulsi", keyword="basil")
        self.assertEqual(self.keywords("Fresh Tulsi").keywords, ["basil"])

    def test_database_alias_beats_name_as_typed(self):
        make_catalog("Chicken", "Chicken Breast")
        IngredientAlias.objects.create(alias="chicken", keyword="chicken breast")
        self.assertEqual(self.keywords("Chicken").keywords, ["chicken breast"])

    def test_non_english_input_can_be_supported_through_an_alias(self):
        make_catalog("Eggs")
        IngredientAlias.objects.create(alias="telur", keyword="eggs")
        self.assertEqual(self.keywords("Telur Ayam").keywords, ["eggs"])

    def test_recipe_name_override_wins(self):
        make_catalog("Chicken Breast", "Chicken")
        result = self.keywords("Chicken Fillet", recipe_name="Chicken Breast")
        self.assertEqual(result.keywords, ["chicken breast"])

    def test_invalid_override_is_skipped_not_replaced_silently(self):
        make_catalog("Chicken")
        result = self.keywords("Chicken", recipe_name="dragonfruit")
        self.assertEqual(result.keywords, [])
        self.assertEqual(result.skipped, ["Chicken"])


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

    def test_header_and_copy_follow_the_new_design(self):
        make_item(self.user, "Garlic", unit="clove", quantity=Decimal("8"))
        response = self.client.get(self.list_url)
        self.assertContains(response, ">Pantry Tracker</h1>")
        self.assertContains(
            response,
            "Track the shelf life of your ingredients with ease. "
            "Get cooking suggestions and early notifications before food goes to waste!",
        )
        self.assertContains(response, "Find recipes from pantry")
        self.assertContains(response, "family=Montserrat")
        self.assertContains(response, "Plus+Jakarta+Sans")
        self.assertContains(response, "8</b> cloves")
        self.assertContains(response, '<html lang="en">')
        # Chip "Inventory" dan sisa teks/URL lama sudah tidak ada
        for old_text in ("Inventory", "pantry-tag", "Simpan", "Hapus",
                         "Kedaluwarsa", "cari-resep"):
            self.assertNotContains(response, old_text)
        self.assertEqual(reverse("pantry:find_recipes"), "/pantry/find-recipes/")

    def test_no_tips_or_invented_stats(self):
        response = self.client.get(self.list_url)
        for text in ("Saved This Month", "Rp", "tips", "Tips"):
            self.assertNotContains(response, text)

    def test_only_own_items_are_listed(self):
        make_item(self.user, "Carrots")
        make_item(self.other, "Milk")
        response = self.client.get(self.list_url)
        self.assertContains(response, "Carrots")
        self.assertNotContains(response, "Milk")

    def test_page_offers_catalog_suggestions_and_loads_toast_css(self):
        make_catalog("Eggs")
        response = self.client.get(self.list_url)
        self.assertContains(response, '<option value="Eggs">', html=False)
        # kolom nama (tambah + edit) dan kolom nama katalog (edit)
        self.assertContains(response, 'list="catalog-ingredients"', count=3)
        self.assertContains(response, "css/toast.css")

    # ----- Summary -----
    def test_total_counts_rows_not_quantity_or_unique_names(self):
        make_item(self.user, "Eggs", quantity=Decimal("12"))
        make_item(self.user, "Eggs", quantity=Decimal("30"))   # nama sama, baris berbeda
        make_item(self.user, "Milk", quantity=Decimal("1"), unit="l")
        make_item(self.other, "Rice")                          # milik user lain
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["total_items"], 3)
        self.assertContains(response, "<strong>3</strong>")

    def test_total_includes_expired_items_still_in_the_pantry(self):
        make_item(self.user, "Old milk", days=-3)
        make_item(self.user, "Eggs", days=10)
        self.assertEqual(self.client.get(self.list_url).context["total_items"], 2)

    def test_expiring_soon_counts_today_and_tomorrow_only(self):
        # Contoh dari brief: 2 bahan hari ini + 1 bahan besok = 3
        make_item(self.user, "Today A", days=0)
        make_item(self.user, "Today B", days=0)
        make_item(self.user, "Tomorrow", days=1)
        make_item(self.user, "Expired", days=-1)
        make_item(self.user, "In two days", days=2)
        make_item(self.user, "Next week", days=7)
        make_item(self.other, "Other user today", days=0)
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["expiring_soon_count"], 3)
        self.assertContains(response, "<strong>3</strong>")
        self.assertContains(response, "items expiring soon")
        self.assertContains(response, "Within the next 48 hours")

    def test_expiring_soon_uses_singular_for_one_item(self):
        make_item(self.user, "Tomorrow", days=1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["expiring_soon_count"], 1)
        self.assertContains(response, ">item expiring soon<")

    def test_summary_is_not_affected_by_category_filter(self):
        make_item(self.user, "Salmon", category="protein", days=0)
        make_item(self.user, "Carrots", category="vegetables", days=5)
        response = self.client.get(self.list_url, {"category": "protein"})
        self.assertEqual(response.context["total_items"], 2)
        self.assertEqual(response.context["expiring_soon_count"], 1)

    # ----- Filter kategori -----
    def _listed(self, **params):
        response = self.client.get(self.list_url, params)
        return response, [item.name for item in response.context["items"]]

    def test_all_items_shows_everything(self):
        make_item(self.user, "Carrots", category="vegetables", days=3)
        make_item(self.user, "Salmon", category="protein", days=2)
        make_item(self.user, "Salt", days=9)  # kategori default: other
        _, names = self._listed()
        self.assertEqual(sorted(names), ["Carrots", "Salmon", "Salt"])

    def test_category_chip_shows_only_that_category(self):
        make_item(self.user, "Carrots", category="vegetables", days=3)
        make_item(self.user, "Spinach", category="vegetables", days=4)
        make_item(self.user, "Salmon", category="protein", days=2)
        make_item(self.user, "Salt", days=9)
        _, names = self._listed(category="vegetables")
        self.assertEqual(sorted(names), ["Carrots", "Spinach"])
        _, names = self._listed(category="protein")
        self.assertEqual(names, ["Salmon"])
        _, names = self._listed(category="fruits")
        self.assertEqual(names, [])

    def test_other_items_only_appear_under_all_items(self):
        make_item(self.user, "Salt", days=9)
        for chip in ("vegetables", "protein", "fruits", "spices", "carbs"):
            with self.subTest(chip=chip):
                self.assertEqual(self._listed(category=chip)[1], [])
        self.assertEqual(self._listed()[1], ["Salt"])

    def test_unknown_or_other_category_param_falls_back_to_all(self):
        make_item(self.user, "Carrots", category="vegetables")
        make_item(self.user, "Salt")
        for value in ("dairy", "other", "<script>"):
            with self.subTest(value=value):
                response, names = self._listed(category=value)
                self.assertEqual(sorted(names), ["Carrots", "Salt"])
                self.assertEqual(response.context["active_category"], "")

    def test_filter_does_not_leak_other_users_items(self):
        make_item(self.other, "Their salmon", category="protein")
        self.assertEqual(self._listed(category="protein")[1], [])

    def test_chips_are_rendered_in_english_and_mark_the_active_one(self):
        response = self.client.get(self.list_url, {"category": "spices"})
        for label in ("All Items", "Vegetables", "Protein", "Fruits",
                      "Spices &amp; Seasonings", "Carbohydrates"):
            self.assertContains(response, f">{label}</a>")
        self.assertEqual(response.context["active_category"], "spices")
        self.assertContains(response, "pantry-chip is-active", count=1)

    def test_empty_category_shows_a_helpful_message(self):
        make_item(self.user, "Carrots", category="vegetables")
        response = self.client.get(self.list_url, {"category": "protein"})
        self.assertContains(response, "No Protein in your pantry yet.")

    def test_category_is_shown_next_to_the_ingredient(self):
        make_item(self.user, "Salmon", category="protein")
        self.assertContains(self.client.get(self.list_url), "<small>Protein</small>")

    # ----- Tambah / edit / hapus -----
    def test_create_with_category_and_storage_radio(self):
        expiry = timezone.localdate() + timedelta(days=7)
        response = self.client.post(self.list_url, {
            "name": "  Chicken   Breast ",
            "category": "protein",
            "quantity": "500",
            "unit": "g",
            "expiry_date": expiry.isoformat(),
            "storage": "freezer",
        })
        self.assertRedirects(response, self.list_url)
        item = PantryItem.objects.get()
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, "Chicken Breast")
        self.assertEqual(item.category, "protein")
        self.assertEqual(item.quantity, Decimal("500"))
        self.assertEqual(item.unit, "g")
        self.assertEqual(item.storage, "freezer")
        self.assertEqual(item.recipe_name, "")

    def test_create_without_category_defaults_to_other(self):
        expiry = timezone.localdate() + timedelta(days=7)
        self.client.post(self.list_url, {
            "name": "Salt", "quantity": "1", "unit": "pack",
            "expiry_date": expiry.isoformat(), "storage": "pantry",
        })
        self.assertEqual(PantryItem.objects.get().category, "other")

    def test_add_form_renders_storage_as_radios_with_a_default(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, 'type="radio" name="storage"', count=3)
        self.assertContains(response, 'value="chiller" checked')
        self.assertContains(response, '<option value="other" selected>Other</option>')

    def test_invalid_add_keeps_the_chosen_storage(self):
        response = self.client.post(self.list_url, {
            "name": "", "category": "protein", "quantity": "1", "unit": "g",
            "expiry_date": "2026-12-01", "storage": "freezer",
        })
        self.assertContains(response, 'value="freezer" checked')

    def test_create_invalid_shows_errors_and_saves_nothing(self):
        response = self.client.post(self.list_url, {
            "name": "", "quantity": "-1", "unit": "g",
            "expiry_date": "", "storage": "freezer",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PantryItem.objects.count(), 0)
        self.assertContains(response, "Ingredient name is required.")
        self.assertContains(response, "Quantity must be greater than 0.")
        self.assertContains(response, "Expiry date is required.")

    def _edit_payload(self, item, **overrides):
        payload = {
            "edit-name": item.name,
            "edit-category": item.category,
            "edit-quantity": "2",
            "edit-unit": "pcs",
            "edit-expiry_date": item.expiry_date.isoformat(),
            "edit-storage": "chiller",
        }
        payload.update(overrides)
        return payload

    def test_edit_quantity(self):
        item = make_item(self.user, quantity=Decimal("4"))
        response = self.client.post(
            reverse("pantry:pantry_edit", args=[item.pk]), self._edit_payload(item)
        )
        self.assertRedirects(response, self.list_url)
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("2"))

    def test_edit_changes_category(self):
        item = make_item(self.user, "Spinach")
        self.assertEqual(item.category, "other")
        self.client.post(
            reverse("pantry:pantry_edit", args=[item.pk]),
            self._edit_payload(item, **{"edit-category": "vegetables"}),
        )
        item.refresh_from_db()
        self.assertEqual(item.category, "vegetables")
        self.assertEqual(self._listed(category="vegetables")[1], ["Spinach"])

    def test_edit_dialog_has_a_category_select_wired_to_the_button(self):
        item = make_item(self.user, "Salmon", category="protein")
        response = self.client.get(self.list_url)
        self.assertContains(response, 'id="id_edit-category"')
        self.assertContains(response, 'data-category="protein"')

    def test_edit_saves_recipe_name(self):
        item = make_item(self.user, "Tulsi")
        self.client.post(
            reverse("pantry:pantry_edit", args=[item.pk]),
            self._edit_payload(item, **{"edit-recipe_name": "  Sweet   Basil "}),
        )
        item.refresh_from_db()
        self.assertEqual(item.recipe_name, "Sweet Basil")

    def test_edit_invalid_keeps_data_and_shows_error(self):
        item = make_item(self.user, quantity=Decimal("4"))
        response = self.client.post(
            reverse("pantry:pantry_edit", args=[item.pk]),
            self._edit_payload(item, **{"edit-quantity": "0"}),
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("4"))
        message = str(list(get_messages(response.wsgi_request))[0])
        self.assertIn("Quantity must be greater than 0.", message)

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
        self.pantry_url = reverse("pantry:pantry_list")
        self.recipes_url = reverse("recipes:recipe_list")
        make_catalog("Eggs", "Carrots", "Chicken", "Basil")

    def _messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_selected_items_only(self):
        eggs = make_item(self.user, "Eggs", days=2)
        make_item(self.user, "Carrots", days=1)
        response = self.client.get(self.url, {"items": [eggs.pk]})
        self.assertRedirects(
            response, catalog_url(self.recipes_url, "eggs"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self._messages(response), [])

    def test_no_selection_uses_all_non_expired(self):
        make_item(self.user, "Eggs", days=2)
        make_item(self.user, "Carrots", days=1)
        make_item(self.user, "Chicken", days=-1)  # expired -> tidak ikut
        response = self.client.get(self.url)
        # urut dari yang paling cepat kedaluwarsa
        self.assertRedirects(
            response, catalog_url(self.recipes_url, "carrots,eggs"),
            fetch_redirect_response=False,
        )

    def test_search_uses_the_whole_pantry_regardless_of_category(self):
        make_item(self.user, "Eggs", category="protein", days=2)
        make_item(self.user, "Carrots", category="vegetables", days=1)
        response = self.client.get(self.url)
        self.assertRedirects(
            response, catalog_url(self.recipes_url, "carrots,eggs"),
            fetch_redirect_response=False,
        )

    def test_unknown_ingredient_is_skipped_and_user_is_told(self):
        make_item(self.user, "Eggs", days=2)
        make_item(self.user, "Dragonfruit", days=3)  # tidak ada di katalog
        response = self.client.get(self.url)
        self.assertRedirects(
            response, catalog_url(self.recipes_url, "eggs"),
            fetch_redirect_response=False,
        )
        messages = self._messages(response)
        self.assertEqual(len(messages), 1)
        self.assertIn("Skipped Dragonfruit", messages[0])
        self.assertNotIn("Eggs", messages[0])

    def test_all_unknown_stays_on_pantry_with_message(self):
        make_item(self.user, "Dragonfruit")
        response = self.client.get(self.url)
        self.assertRedirects(response, self.pantry_url, fetch_redirect_response=False)
        self.assertIn("Dragonfruit", self._messages(response)[0])

    def test_empty_catalog_stays_on_pantry_with_message(self):
        RecipeIngredient.objects.all().delete()
        make_item(self.user, "Eggs")
        response = self.client.get(self.url)
        self.assertRedirects(response, self.pantry_url, fetch_redirect_response=False)
        self.assertIn("recipe catalog is empty", self._messages(response)[0])

    def test_alias_and_override_are_used(self):
        IngredientAlias.objects.create(alias="tulsi", keyword="basil")
        make_item(self.user, "Tulsi", days=2)
        make_item(self.user, "Chicken Thigh", days=3, recipe_name="chicken")
        response = self.client.get(self.url)
        self.assertRedirects(
            response, catalog_url(self.recipes_url, "basil,chicken"),
            fetch_redirect_response=False,
        )

    def test_expired_item_is_never_searched_even_if_selected(self):
        old = make_item(self.user, "Chicken", days=-1)
        response = self.client.get(self.url, {"items": [old.pk]})
        self.assertRedirects(response, self.pantry_url, fetch_redirect_response=False)

    def test_other_users_items_are_ignored(self):
        other = User.objects.create_user("lain", password="pw12345!")
        theirs = make_item(other, "Eggs")
        response = self.client.get(self.url, {"items": [theirs.pk]})
        self.assertRedirects(response, self.pantry_url, fetch_redirect_response=False)

    def test_skip_message_is_visible_on_catalog_page(self):
        make_item(self.user, "Eggs", days=2)
        make_item(self.user, "Dragonfruit", days=3)
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "Skipped Dragonfruit")
        self.assertContains(response, "css/toast.css")

    def test_catalog_actually_filters_by_the_redirect(self):
        Recipe.objects.create(mealdb_id="test-2", name="Plain Rice")
        item = make_item(self.user, "Eggs")
        response = self.client.get(self.url, {"items": [item.pk]}, follow=True)
        self.assertContains(response, "Test Dish")
        self.assertNotContains(response, "Plain Rice")
