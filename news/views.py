from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.vary import vary_on_headers
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .browsing import add_coverages, article_batch, articles_for, category_image, filter_articles, story_articles
from .briefings import briefing_context
from .forms import PreferenceForm, RegistrationForm
from .models import Article, SavedArticle, UserPreference
from .retention import retention_cutoff


def home(request):
    if request.user.is_authenticated:
        return redirect("news_feed")
    return render(request, "news/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("preferences")

    form = RegistrationForm(request.POST or None)
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
    sections = [
        {"category": category, "image": category_image(category.slug),
         "article_count": story_articles(articles_for([category], preference.classification_mode)).count()}
        for category in categories
    ]

    now = timezone.now()
    now_local = timezone.localtime(now)
    if now_local.hour < 12:
        greeting = "Buenos días"
    elif now_local.hour < 20:
        greeting = "Buenas tardes"
    else:
        greeting = "Buenas noches"
    first_name = request.user.first_name.strip()
    display_name = first_name.split(maxsplit=1)[0] if first_name else request.user.username
    return render(request, "news/feed.html", {
        "sections": sections, "greeting": greeting,
        "display_name": display_name,
        **briefing_context(now, categories),
    })


@login_required
@vary_on_headers("Accept")
def category_news(request, slug):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    category = get_object_or_404(preference.categories, slug=slug)
    available = articles_for([category], preference.classification_mode)
    form, articles, text = filter_articles(request, available)
    sort = form.cleaned_data.get("sort", "") if not form.errors else ""
    articles = story_articles(articles, text if not form.errors and sort != "recent" else "")
    filters = {key: request.GET.get(key, "").strip() for key in ("source", "language", "q", "period", "sort")}
    day = str(timezone.localdate()) if filters["period"] == "today" else ""
    cursor_context = [category.pk, preference.classification_mode, filters, day]
    response_status = 200
    try:
        rows, next_url = article_batch(request, articles, cursor_context, text if not form.errors else "", sort)
    except ValueError as error:
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": str(error)}, status=400)
        form.add_error(None, str(error))
        rows, next_url, response_status = [], None, 400
    is_json = "application/json" in request.headers.get("Accept", "")
    add_coverages(rows)
    leading_label = "La más reciente"
    if sort == "important":
        leading_label = "La más importante" if rows and rows[0].importance else "Pendiente de evaluación"
    context = {
        "category": category, "category_image": category_image(slug),
        "articles": rows, "article_count": articles.count(),
        "leading": bool(rows) and not text and not is_json,
        "filter_form": form, "search_text": text, "sort": sort,
        "leading_label": leading_label,
        "filters_active": any(filters.values()), "next_url": next_url,
        "saved_ids": set(SavedArticle.objects.filter(user=request.user, article__in=rows).values_list("article_id", flat=True)),
    }
    if is_json:
        return JsonResponse({
            "html": render_to_string("news/article_cards.html", context, request=request),
            "next_url": next_url,
        })
    return render(request, "news/category.html", context, status=response_status)


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
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"saved": True, "action": reverse("remove_saved_article", args=[article_id])})
    messages.success(request, "Noticia guardada.")
    return article_redirect(request)


@login_required
@require_POST
def remove_saved_article(request, article_id):
    SavedArticle.objects.filter(user=request.user, article_id=article_id).delete()
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"saved": False, "action": reverse("save_article", args=[article_id])})
    messages.success(request, "Noticia quitada de tus guardadas.")
    return article_redirect(request)


def article_redirect(request):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("saved_articles")
