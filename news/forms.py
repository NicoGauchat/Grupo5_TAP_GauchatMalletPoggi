from django import forms

from .models import UserPreference


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ["categories"]
        widgets = {"categories": forms.CheckboxSelectMultiple}
