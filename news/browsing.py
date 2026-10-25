from datetime import datetime

from django.core import signing
from django.db import connection
from django.db.models import FloatField, Q
from django.db.models.functions import Cast

from .forms import NewsFilterForm
from .models import Article, UserPreference
from .retention import retention_cutoff
from .search import search_articles


CATEGORY_IMAGES = {"argentina", "politica-argentina", "geopolitica", "economia", "mercados-finanzas",
                   "tecnologia", "inteligencia-artificial", "ciencia"}
CURSOR_SALT = "news.category"


def category_image(slug):
    return f"news/images/{slug if slug in CATEGORY_IMAGES else 'geopolitica'}.webp"


def articles_for(categories, mode):
    match = Q(categories__in=categories)
    if mode == UserPreference.CLASSIFICATION_AI:
        match = Q(llm_categories__in=categories)
    elif mode == UserPreference.CLASSIFICATION_BOTH:
        match |= Q(llm_categories__in=categories)
    return Article.objects.filter(
        match, feed__is_active=True, published_at__gte=retention_cutoff(),
    ).distinct()


def filter_articles(request, articles):
    form = NewsFilterForm(request.GET, articles=articles)
    if not form.is_valid():
        return form, articles.none(), ""
    source, language, text = (form.cleaned_data[key] for key in ("source", "language", "q"))
    if source:
        articles = articles.filter(feed__source=source)
    if language:
        articles = articles.filter(language=language)
    if text:
        if connection.vendor != "postgresql":
            form.add_error("q", "La búsqueda no está disponible en este entorno.")
            return form, articles.none(), text
        articles = search_articles(articles, text)
    return form, articles, text


def article_batch(request, articles, context, search_text):
    if search_text:
        articles = articles.annotate(relevance=Cast("relevance", FloatField()))
    fields = (["relevance"] if search_text else []) + ["published_at", "pk"]
    articles = articles.select_related("feed__source").order_by(*[f"-{field}" for field in fields])
    is_json = "application/json" in request.headers.get("Accept", "")
    visible = request.GET.get("visible", "10")
    if not visible.isascii() or not visible.isdecimal() or len(visible) > 6:
        raise ValueError("Cantidad de noticias inválida.")
    limit, seen = max(10, int(visible)), 0
    token = request.GET.get("cursor")
    if token:
        try:
            cursor = signing.loads(token, salt=CURSOR_SALT, max_age=14 * 86400)
            if cursor["context"] != context or type(cursor["seen"]) is not int or cursor["seen"] < 0:
                raise ValueError
            values = cursor["after"]
            if len(values) != len(fields):
                raise ValueError
            values[-2] = datetime.fromisoformat(values[-2])
            if values[-2].tzinfo is None or type(values[-1]) is not int:
                raise ValueError
            if search_text and (type(values[0]) not in (int, float) or not 0 <= values[0] < float("inf")):
                raise ValueError
        except (signing.BadSignature, KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError("El enlace de continuación venció o no corresponde a estos filtros.") from error
        if is_json:
            after, prefix = Q(), {}
            for field, value in zip(fields, values):
                after |= Q(**prefix, **{f"{field}__lt": value})
                prefix[field] = value
            articles = articles.filter(after)
            limit, seen = 9, cursor["seen"]
    rows = list(articles[:limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    seen += len(rows)
    next_url = None
    if has_more:
        last = rows[-1]
        values = [getattr(last, field) for field in fields]
        values[-2] = values[-2].isoformat()
        token = signing.dumps({"context": context, "after": values, "seen": seen}, salt=CURSOR_SALT, compress=True)
        query = request.GET.copy()
        query["cursor"], query["visible"] = token, str(seen + 9)
        next_url = f"{request.path}?{query.urlencode()}"
    return rows, next_url
