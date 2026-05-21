from django import forms
from .models import Bahan

class BahanForm(forms.ModelForm):
    class Meta:
        model = Bahan
        fields = ["nama", "kategori", "satuan"]

        widgets = {
            "nama": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nama bahan"
            }),
            "kategori": forms.Select(attrs={
                "class": "form-select"
            }),
            "satuan": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "kg / gram / liter"
            }),
        }