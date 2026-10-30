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
                    "placeholder": "Ingredients you want to buy (e.g. eggs)...",
                    "maxlength": 100,
                    "autocomplete": "off",
                }
            ),
            "quantity": forms.TextInput(
                attrs={
                    "class": "shop-input shop-input--qty",
                    "placeholder": "quantity (e.g., 1 pc)",
                    "maxlength": 50,
                    "autocomplete": "off",
                }
            ),
        }
        error_messages = {
            "name": {"required": "Material name is required."},
        }

    def clean_name(self):
        # "  tempe   goreng " -> "tempe goreng"
        name = re.sub(r"\s+", " ", self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Material name is required")
        return name

    def clean_quantity(self):
        return re.sub(r"\s+", " ", self.cleaned_data.get("quantity", "")).strip()
