
from django import forms
from .models import Favorite


class FavoriteNoteForm(forms.ModelForm):
    class Meta:
        model = Favorite
        fields = ["personal_note"]

        widgets = {
            "personal_note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tulis catatan pribadimu tentang resep ini...",
                }
            )
        }
