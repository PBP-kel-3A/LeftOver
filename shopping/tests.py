from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from pantry.models import PantryItem

from .models import ShoppingItem


class PantryQuantityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budi", password="pw12345!")

    def parse(self, text):
        return ShoppingItem(user=self.user, name="x", quantity=text).pantry_quantity()

    def test_number_and_unit(self):
        self.assertEqual(self.parse("2 botol"), (Decimal("2"), "pcs"))
        self.assertEqual(self.parse("500gr"), (Decimal("500"), "g"))
        self.assertEqual(self.parse("1,5 kg"), (Decimal("1.5"), "kg"))
        self.assertEqual(self.parse("3 siung"), (Decimal("3"), "clove"))

    def test_fallback_to_one_pcs(self):
        self.assertEqual(self.parse(""), (Decimal("1"), "pcs"))
        self.assertEqual(self.parse("yang pedas"), (Decimal("1"), "pcs"))
        self.assertEqual(self.parse("0 pcs"), (Decimal("1"), "pcs"))
        self.assertEqual(self.parse("2 mangkok"), (Decimal("2"), "pcs"))


class ShoppingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budi", password="pw12345!")
        self.other = User.objects.create_user("sari", password="pw12345!")
        self.client.login(username="budi", password="pw12345!")

    def make_item(self, user=None, **kwargs):
        defaults = {"name": "Kecap", "quantity": "1 botol"}
        defaults.update(kwargs)
        return ShoppingItem.objects.create(user=user or self.user, **defaults)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("shopping:shopping_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)

    def test_list_shows_only_own_items_and_counts(self):
        self.make_item(name="Tempe")
        self.make_item(name="Tahu", is_purchased=True)
        self.make_item(user=self.other, name="Rahasia")

        response = self.client.get(reverse("shopping:shopping_list"))

        self.assertContains(response, "Tempe")
        self.assertContains(response, "Tahu")
        self.assertNotContains(response, "Rahasia")
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["pending_count"], 1)
        self.assertEqual(response.context["purchased_count"], 1)

    def test_add_item(self):
        response = self.client.post(
            reverse("shopping:shopping_add"),
            {"name": "  Tempe   goreng ", "quantity": "2 papan"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        item = ShoppingItem.objects.get(user=self.user)
        self.assertEqual(item.name, "Tempe goreng")
        self.assertEqual(item.quantity, "2 papan")
        self.assertIn("Tempe goreng", response.json()["html"])

    def test_add_item_requires_name(self):
        response = self.client.post(reverse("shopping:shopping_add"), {"name": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ShoppingItem.objects.exists())

    def test_toggle_purchased(self):
        item = self.make_item()
        url = reverse("shopping:shopping_toggle", args=[item.pk])

        self.assertTrue(self.client.post(url).json()["is_purchased"])
        self.assertFalse(self.client.post(url).json()["is_purchased"])

    def test_cannot_touch_other_users_items(self):
        item = self.make_item(user=self.other)

        toggle = self.client.post(reverse("shopping:shopping_toggle", args=[item.pk]))
        delete = self.client.post(reverse("shopping:shopping_delete", args=[item.pk]))

        self.assertEqual(toggle.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        self.assertTrue(ShoppingItem.objects.filter(pk=item.pk).exists())

    def test_delete_item(self):
        item = self.make_item()

        response = self.client.post(reverse("shopping:shopping_delete", args=[item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ShoppingItem.objects.filter(pk=item.pk).exists())

    def test_get_not_allowed_on_actions(self):
        item = self.make_item()
        response = self.client.get(reverse("shopping:shopping_delete", args=[item.pk]))
        self.assertEqual(response.status_code, 405)

    def test_transfer_moves_only_purchased_items(self):
        bought = self.make_item(name="Telur", quantity="10 butir", is_purchased=True)
        self.make_item(name="Gula", is_purchased=False)
        self.make_item(user=self.other, name="Susu", is_purchased=True)

        response = self.client.post(reverse("shopping:transfer_to_pantry"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["moved_ids"], [bought.pk])

        pantry = PantryItem.objects.get(user=self.user)
        self.assertEqual(pantry.name, "Telur")
        self.assertEqual(pantry.quantity, Decimal("10"))
        self.assertEqual(pantry.unit, "pcs")

        # Yang sudah dipindah hilang dari daftar, sisanya tetap
        self.assertEqual(
            list(ShoppingItem.objects.filter(user=self.user).values_list("name", flat=True)),
            ["Gula"],
        )
        self.assertFalse(PantryItem.objects.filter(user=self.other).exists())

    def test_transfer_with_nothing_purchased(self):
        self.make_item(is_purchased=False)

        response = self.client.post(reverse("shopping:transfer_to_pantry"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PantryItem.objects.exists())
