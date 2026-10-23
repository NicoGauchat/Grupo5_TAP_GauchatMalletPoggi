from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import NewsFilterForm, PreferenceForm
from .models import Article, NewsBriefing, SavedArticle, UserPreference
from .retention import retention_cutoff
from .search import search_articles


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
    mode = preference.classification_mode
    if mode == UserPreference.CLASSIFICATION_RULES:
        category_filter = Q(categories__in=categories)
    elif mode == UserPreference.CLASSIFICATION_AI:
        category_filter = Q(llm_categories__in=categories)
    else:
        category_filter = Q(categories__in=categories) | Q(llm_categories__in=categories)
    available_articles = Article.objects.filter(
        category_filter, feed__is_active=True,
        published_at__gte=retention_cutoff(),
    ).distinct()
    filter_form = NewsFilterForm(request.GET, articles=available_articles)
    filtered_articles = available_articles
    filters_active = False
    search_text = ""
    if filter_form.is_valid():
        source = filter_form.cleaned_data["source"]
        language = filter_form.cleaned_data["language"]
        if source:
            filtered_articles = filtered_articles.filter(feed__source=source)
        if language:
            filtered_articles = filtered_articles.filter(language=language)
        search_text = filter_form.cleaned_data["q"]
        if search_text:
            if connection.vendor == "postgresql":
                filtered_articles = search_articles(filtered_articles, search_text)
            else:
                filter_form.add_error("q", "La búsqueda no está disponible en este entorno.")
                filtered_articles = available_articles.none()
        filters_active = bool(source or language or search_text)
    else:
        # Una URL con filtros inválidos no debe mostrar resultados sin filtrar.
        filtered_articles = available_articles.none()
    sections = []
    for category in categories:
        if mode == UserPreference.CLASSIFICATION_RULES:
            section_filter = Q(categories=category)
        elif mode == UserPreference.CLASSIFICATION_AI:
            section_filter = Q(llm_categories=category)
        else:
            section_filter = Q(categories=category) | Q(llm_categories=category)
        category_articles = (
            filtered_articles.filter(section_filter).distinct()
            .select_related("feed__source").order_by(
                *(["-relevance"] if search_text and not filter_form.errors else []), "-published_at", "-id",
            )
        )
        paginator = Paginator(category_articles, ARTICLES_PER_CATEGORY)
        page_key = f"page_{category.slug}"
        try:
            page_number = max(1, int(request.GET.get(page_key, "1")))
        except ValueError:
            page_number = 1
        page = paginator.get_page(page_number)

        def page_url(number):
            query = request.GET.copy()
            query[page_key] = str(number)
            return f"{request.path}?{query.urlencode()}#category-{category.slug}"

        sections.append(
            {
                "category": category, "article_count": paginator.count,
                "articles": list(page.object_list), "page": page,
                "previous_url": page_url(page.previous_page_number()) if page.has_previous() else None,
                "next_url": page_url(page.next_page_number()) if page.has_next() else None,
            }
        )

    # La lista de categorías ya viene en orden alfabético: en un empate se conserva.
    sections.sort(key=lambda section: -section["article_count"])

    now = timezone.now()
    now_local = timezone.localtime(now)
    if now_local.hour < 12:
        greeting = "Buenos días"
    elif now_local.hour < 20:
        greeting = "Buenas tardes"
    else:
        greeting = "Buenas noches"
    briefing_cutoff = now - timedelta(hours=24)
    briefing = NewsBriefing.objects.filter(
        generated_at__gte=briefing_cutoff,
    ).exclude(
        items__articles__published_at__lt=briefing_cutoff,
    ).exclude(
        items__articles__feed__allow_ai_briefing=False,
    ).distinct().prefetch_related(
        "items__articles__feed__source",
    ).first()

    return render(request, "news/feed.html", {
        "sections": sections, "filter_form": filter_form,
        "filters_active": filters_active,
        "search_text": search_text,
        "has_articles": any(section["article_count"] for section in sections),
        "saved_ids": set(SavedArticle.objects.filter(user=request.user).values_list("article_id", flat=True)),
        "greeting": greeting,
        "briefing": briefing,
    })


@login_required
def saved_articles(request):
    saved = SavedArticle.objects.filter(
        user=request.user, article__published_at__gte=retention_cutoff(),
    ).select_related("article__feed__source")
    page = Paginator(saved, 10).get_page(request.GET.get("page"))
    return render(request, "news/saved_articles.html", {"page": page})


@login_required
@require_POST
def save_article(request, article_id):
    article = get_object_or_404(
        Article, pk=article_id, feed__is_active=True, published_at__gte=retention_cutoff(),
    )
    SavedArticle.objects.get_or_create(user=request.user, article=article)
    messages.success(request, "Noticia guardada.")
    return article_redirect(request)


@login_required
@require_POST
def remove_saved_article(request, article_id):
    SavedArticle.objects.filter(user=request.user, article_id=article_id).delete()
    messages.success(request, "Noticia quitada de tus guardadas.")
    return article_redirect(request)


def article_redirect(request):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("saved_articles")
