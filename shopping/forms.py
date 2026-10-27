import re

from django import forms

from .models import ShoppingItem


class ShoppingItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingItem
        fields = ["name", "quantity"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "shop-input shop-input--name",
                    "placeholder": "Bahan yang ingin dibeli (cth : tempe) ...",
                    "maxlength": 100,
                    "autocomplete": "off",
                }
            ),
            "quantity": forms.TextInput(
                attrs={
                    "class": "shop-input shop-input--qty",
                    "placeholder": "jumlah (cth: 1 pics)",
                    "maxlength": 50,
                    "autocomplete": "off",
                }
            ),
        }
        error_messages = {
            "name": {"required": "Nama bahan wajib diisi."},
        }

    def clean_name(self):
        # "  tempe   goreng " -> "tempe goreng"
        name = re.sub(r"\s+", " ", self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Nama bahan wajib diisi.")
        return name

    def clean_quantity(self):
        return re.sub(r"\s+", " ", self.cleaned_data.get("quantity", "")).strip()
