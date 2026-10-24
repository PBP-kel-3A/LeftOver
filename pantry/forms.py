import re

from django import forms

from .models import PantryItem

INPUT_CLASS = "pantry-input"


class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItem
        fields = ["name", "quantity", "unit", "expiry_date", "storage"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Misal: Telur Ayam, Wortel...",
                    "maxlength": 100,
                    "autocomplete": "off",
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
        }
        labels = {
            "name": "Nama Bahan Dapur",
            "quantity": "Jumlah",
            "unit": "Satuan",
            "expiry_date": "Perkiraan Kedaluwarsa",
            "storage": "Kategori Tempat Simpan",
        }
        error_messages = {
            "name": {"required": "Nama bahan wajib diisi."},
            "quantity": {
                "required": "Jumlah wajib diisi.",
                "invalid": "Masukkan angka yang valid.",
                "min_value": "Jumlah harus lebih dari 0.",
            },
            "expiry_date": {
                "required": "Tanggal kedaluwarsa wajib diisi.",
                "invalid": "Format tanggal tidak valid.",
            },
        }

    def clean_name(self):
        # Rapikan spasi berlebih: "  telur   ayam " -> "telur ayam"
        name = re.sub(r"\s+", " ", self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Nama bahan wajib diisi.")
        return name
