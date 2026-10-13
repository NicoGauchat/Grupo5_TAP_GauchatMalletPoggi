from django import forms

from .models import Source, UserPreference


class NewsFilterForm(forms.Form):
    q = forms.CharField(
        label="Buscar en títulos", required=False, max_length=200,
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Ejemplo: inteligencia artificial"}),
    )
    source = forms.ModelChoiceField(
        label="Fuente", queryset=Source.objects.none(), required=False,
        empty_label="Todas las fuentes",
    )
    language = forms.ChoiceField(label="Idioma", required=False)

    def __init__(self, *args, articles, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = Source.objects.filter(
            pk__in=articles.values("feed__source_id")
        )
        languages = articles.exclude(language="").order_by("language").values_list(
            "language", flat=True
        ).distinct()
        names = {"es": "Español", "en": "Inglés", "pt": "Portugués"}
        self.fields["language"].choices = [("", "Todos los idiomas")] + [
            (language, names.get(language.lower(), language.upper()))
            for language in languages
        ]


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ["categories"]
        widgets = {"categories": forms.CheckboxSelectMultiple}
