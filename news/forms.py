from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Source, UserPreference


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre real", max_length=150,
        help_text="Usaremos solo tu primer nombre para saludarte.",
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "first_name")

    def clean_first_name(self):
        return " ".join(self.cleaned_data["first_name"].split())


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
    period = forms.ChoiceField(label="Fecha", required=False, choices=[
        ("", "Últimos 14 días"), ("today", "Hoy"), ("24h", "Últimas 24 horas"),
        ("3d", "Últimos 3 días"), ("7d", "Última semana"),
    ])
    sort = forms.ChoiceField(label="Orden", required=False, choices=[
        ("important", "Más importantes"), ("recent", "Más recientes"),
    ])

    def __init__(self, *args, articles, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data.get("q", "").strip():
            self.fields["sort"].choices = [
                ("", "Relevancia de búsqueda"), ("recent", "Más recientes"), ("important", "Más importantes"),
            ]
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classification_mode"].required = False

    def clean_classification_mode(self):
        return self.cleaned_data["classification_mode"] or (
            self.instance.classification_mode or UserPreference.CLASSIFICATION_BOTH
        )

    class Meta:
        model = UserPreference
        fields = ["categories", "classification_mode"]
        widgets = {"categories": forms.CheckboxSelectMultiple, "classification_mode": forms.RadioSelect}
