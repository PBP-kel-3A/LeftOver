import re

from django import forms

from .models import PantryItem

INPUT_CLASS = "pantry-input"
CATALOG_DATALIST_ID = "catalog-ingredients"  # <datalist> in pantry_list.html


class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItem
        fields = ["name", "quantity", "unit", "expiry_date", "storage", "recipe_name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. Eggs, Carrots...",
                    "maxlength": 100,
                    "autocomplete": "off",
                    # Suggest names that exist in the recipe catalog, so what the
                    # user types matches the catalog without any translation.
                    "list": CATALOG_DATALIST_ID,
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0",
                    "min": "0.01",
                    "step": "any",
                }
            ),
            "unit": forms.Select(attrs={"class": INPUT_CLASS}),
            "expiry_date": forms.DateInput(
                attrs={"class": INPUT_CLASS, "type": "date"},
                format="%Y-%m-%d",
            ),
            "storage": forms.Select(attrs={"class": INPUT_CLASS}),
            "recipe_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. eggs, chicken breast",
                    "maxlength": 100,
                    "autocomplete": "off",
                    "list": CATALOG_DATALIST_ID,
                }
            ),
        }
        labels = {
            "name": "Ingredient Name",
            "quantity": "Quantity",
            "unit": "Unit",
            "expiry_date": "Estimated Expiry Date",
            "storage": "Storage Location",
            "recipe_name": "Recipe Catalog Name (optional)",
        }
        error_messages = {
            "name": {"required": "Ingredient name is required."},
            "quantity": {
                "required": "Quantity is required.",
                "invalid": "Enter a valid number.",
                "min_value": "Quantity must be greater than 0.",
            },
            "expiry_date": {
                "required": "Expiry date is required.",
                "invalid": "Enter a valid date.",
            },
        }

    def clean_name(self):
        # Tidy up extra spaces: "  fresh   eggs " -> "fresh eggs"
        name = re.sub(r"\s+", " ", self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Ingredient name is required.")
        return name

    def clean_recipe_name(self):
        return re.sub(r"\s+", " ", self.cleaned_data.get("recipe_name", "")).strip()
