"""Tes jalur AJAX untuk form tambah & edit bahan (fetch() dari pantry.js).

Jalur non-AJAX (form biasa tanpa JavaScript) tetap diuji di sini supaya
terbukti perilakunya tidak berubah.
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import PantryItem

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def _offline(*args, **kwargs):
    raise requests.ConnectionError("tes tidak boleh memanggil TheMealDB")


# Halaman yang dirender ulang memanggil catalog_ingredient_names(); jaringan dimatikan
offline_catalog = mock.patch("requests.get", new=_offline)


def make_item(user, name="Eggs", days=5, **kwargs):
    defaults = {"quantity": Decimal("4"), "unit": "pcs"}
    defaults.update(kwargs)
    return PantryItem.objects.create(
        user=user, name=name,
        expiry_date=timezone.localdate() + timedelta(days=days), **defaults,
    )


@offline_catalog
class AjaxAddFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")
        self.client.login(username="rahmi", password="pw12345!")
        self.url = reverse("pantry:pantry_list")
        self.valid = {
            "name": "Eggs", "category": "protein", "quantity": "4", "unit": "pcs",
            "expiry_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
            "storage": "chiller",
        }

    def messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_valid_ajax_saves_and_answers_with_json(self):
        response = self.client.post(self.url, self.valid, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"ok": True, "redirect": self.url})
        item = PantryItem.objects.get()
        self.assertEqual((item.user, item.name, item.category), (self.user, "Eggs", "protein"))
        # Toast tetap lewat Django messages, tampil di halaman berikutnya
        self.assertEqual(self.messages(response), ["Eggs was added to your pantry."])

    def test_invalid_ajax_returns_400_with_errors_and_saves_nothing(self):
        response = self.client.post(
            self.url, {"name": "  ", "quantity": "-1", "unit": "pcs", "expiry_date": "", "storage": "chiller"}, **AJAX
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["errors"], {
            "name": ["Ingredient name is required."],
            "quantity": ["Quantity must be greater than 0."],
            "expiry_date": ["Expiry date is required."],
        })
        self.assertEqual(PantryItem.objects.count(), 0)
        self.assertEqual(self.messages(response), [])  # tidak ada toast yang menumpuk

    def test_invalid_choice_is_reported_against_the_right_input(self):
        response = self.client.post(self.url, {**self.valid, "storage": "garage", "category": "dairy"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(sorted(response.json()["errors"]), ["category", "storage"])

    def test_without_the_header_nothing_changes(self):
        # Form biasa (tanpa JS): valid -> redirect, tidak valid -> halaman HTML dengan error
        ok = self.client.post(self.url, self.valid)
        self.assertRedirects(ok, self.url)
        bad = self.client.post(self.url, {**self.valid, "name": ""})
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "Ingredient name is required.")
        self.assertEqual(PantryItem.objects.count(), 1)

    def test_ajax_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url, self.valid, **AJAX)
        self.assertRedirects(response, f"{reverse('main:login')}?next={self.url}")
        self.assertEqual(PantryItem.objects.count(), 0)

    def test_csrf_is_still_enforced(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="rahmi", password="pw12345!")
        self.assertEqual(strict.post(self.url, self.valid, **AJAX).status_code, 403)
        self.assertEqual(PantryItem.objects.count(), 0)


@offline_catalog
class AjaxEditFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rahmi", password="pw12345!")
        self.other = User.objects.create_user("lain", password="pw12345!")
        self.client.login(username="rahmi", password="pw12345!")
        self.item = make_item(self.user, "Eggs", quantity=Decimal("4"))
        self.url = reverse("pantry:pantry_edit", args=[self.item.pk])
        self.list_url = reverse("pantry:pantry_list")

    def payload(self, **overrides):
        data = {
            "edit-name": "Eggs", "edit-category": "other", "edit-quantity": "2", "edit-unit": "pcs",
            "edit-expiry_date": self.item.expiry_date.isoformat(), "edit-storage": "chiller",
        }
        data.update(overrides)
        return data

    def test_valid_ajax_updates_and_answers_with_json(self):
        response = self.client.post(self.url, self.payload(), **AJAX)
        self.assertEqual(response.json(), {"ok": True, "redirect": self.list_url})
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("2"))
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], ["Eggs was updated."])

    def test_invalid_ajax_errors_use_the_prefixed_input_names(self):
        response = self.client.post(self.url, self.payload(**{"edit-quantity": "0", "edit-name": ""}), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {
            "edit-name": ["Ingredient name is required."],
            "edit-quantity": ["Quantity must be greater than 0."],
        })
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("4"))  # tidak berubah
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], [])

    def test_without_the_header_invalid_edit_still_redirects_with_a_toast(self):
        response = self.client.post(self.url, self.payload(**{"edit-quantity": "0"}))
        self.assertRedirects(response, self.list_url)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertEqual(messages, ["Couldn't save your changes: Quantity must be greater than 0."])

    def test_other_users_item_is_still_404_for_ajax(self):
        theirs = make_item(self.other, "Milk")
        response = self.client.post(reverse("pantry:pantry_edit", args=[theirs.pk]), self.payload(), **AJAX)
        self.assertEqual(response.status_code, 404)


@offline_catalog
class AjaxMarkupTests(TestCase):
    def test_add_and_edit_forms_opt_in_but_delete_form_does_not(self):
        User.objects.create_user("rahmi", password="pw12345!")
        self.client.login(username="rahmi", password="pw12345!")
        html = self.client.get(reverse("pantry:pantry_list")).content.decode()
        self.assertEqual(html.count("data-ajax-form"), 2)
        self.assertIn('id="edit-form" class="pantry-form" novalidate data-ajax-form', html)
        delete_form = html[html.index('id="delete-form"'):]
        self.assertNotIn("data-ajax-form", delete_form[: delete_form.index(">")])
