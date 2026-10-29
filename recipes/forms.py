from urllib.parse import urlparse

from django import forms
from django.core.exceptions import ValidationError

from .models import Recipe




class RecipeForm(forms.ModelForm):
    ingredients_text = forms.CharField(
        label="Bahan dan Takaran",
        required=True,
        max_length=10000,
        help_text=(
            "Masukkan satu bahan per baris dengan format: "
            "nama bahan | takaran. Contoh: Chicken | 200 g"
        ),
        widget=forms.Textarea(attrs={
            "class": "form-input",
            "rows": 6,
            "placeholder": (
                "Chicken | 200 g\n"
                "Garlic | 2 cloves\n"
                "Salt | 1 tsp"
            ),
        }),
    )

    def clean_youtube_url(self):
        url = self.cleaned_data.get("youtube_url")

        if not url:
            return url

        parsed_url = urlparse(url)
        hostname = (parsed_url.hostname or "").lower()

        allowed_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
            "www.youtube-nocookie.com",
            "youtube-nocookie.com",
        }

        if (
            parsed_url.scheme != "https"
            or hostname not in allowed_hosts
        ):
            raise ValidationError(
                "Masukkan URL video dari domain YouTube yang valid."
            )

        return url
    
    class Meta:
        model = Recipe
        fields = [
            "name",
            "alternate_name",
            "category",
            "area",
            "country",
            "instructions",
            "image_url",
            "youtube_url",
            "tags",
            "source_url",
        ]

        labels = {
            "name": "Nama Resep",
            "alternate_name": "Nama Alternatif",
            "category": "Kategori",
            "area": "Asal Masakan",
            "country": "Negara",
            "instructions": "Instruksi Memasak",
            "image_url": "URL Gambar",
            "youtube_url": "URL Video YouTube",
            "tags": "Tags",
            "source_url": "URL Sumber Resep",
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Contoh: Nasi Goreng",
            }),
            "alternate_name": forms.TextInput(attrs={
                "class": "form-input",
            }),
            "category": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Contoh: Chicken",
            }),
            "area": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Contoh: Indonesian",
            }),
            "country": forms.TextInput(attrs={
                "class": "form-input",
            }),
            "instructions": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 6,
                "placeholder": "Tuliskan langkah-langkah memasak...",
            }),
            "image_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "https://...",
            }),
            "youtube_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "https://www.youtube.com/...",
            }),
            "tags": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Contoh: easy, dinner",
            }),
            "source_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "https://...",
            }),
        }
