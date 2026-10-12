from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .forms import NewsFilterForm, PreferenceForm
from .models import Article, UserPreference
from .retention import retention_cutoff


ARTICLES_PER_CATEGORY = 10


def home(request):
    if request.user.is_authenticated:
        return redirect("news_feed")
    return render(request, "news/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("preferences")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("preferences")

    return render(request, "news/register.html", {"form": form})


@login_required
def preferences(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    form = PreferenceForm(request.POST or None, instance=preference)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tus categorías se guardaron.")
        return redirect("news_feed")

    return render(request, "news/preferences.html", {"form": form})


@login_required
def news_feed(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    categories = list(preference.categories.all())
    available_articles = Article.objects.filter(
        categories__in=categories, feed__is_active=True,
        published_at__gte=retention_cutoff(),
    ).distinct()
    filter_form = NewsFilterForm(request.GET, articles=available_articles)
    filtered_articles = available_articles
    filters_active = False
    if filter_form.is_valid():
        source = filter_form.cleaned_data["source"]
        language = filter_form.cleaned_data["language"]
        if source:
            filtered_articles = filtered_articles.filter(feed__source=source)
        if language:
            filtered_articles = filtered_articles.filter(language=language)
        filters_active = bool(source or language)
    else:
        # Una URL con filtros inválidos no debe mostrar resultados sin filtrar.
        filtered_articles = available_articles.none()
    sections = []
    for category in categories:
        category_articles = filtered_articles.filter(categories=category)
        article_count = category_articles.count()
        articles = list(
            category_articles.select_related("feed__source")
            .order_by("-published_at", "-id")[:ARTICLES_PER_CATEGORY]
        )
        sections.append(
            {"category": category, "article_count": article_count, "articles": articles}
        )

    # La lista de categorías ya viene en orden alfabético: en un empate se conserva.
    sections.sort(key=lambda section: -section["article_count"])

    return render(request, "news/feed.html", {
        "sections": sections, "filter_form": filter_form,
        "filters_active": filters_active,
    })
