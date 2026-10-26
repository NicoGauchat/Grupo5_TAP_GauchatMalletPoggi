from datetime import datetime, timedelta

from django.core import signing
from django.db import connection
from django.db.models import Case, FloatField, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast
from django.utils import timezone

from .forms import NewsFilterForm
from .models import GROUPING_VERSION, Article, UserPreference
from .retention import retention_cutoff
from .search import search_articles


CATEGORY_IMAGES = {"argentina", "politica-argentina", "geopolitica", "economia", "mercados-finanzas",
                   "tecnologia", "inteligencia-artificial", "ciencia"}
CURSOR_SALT = "news.category.stories.v3"


def category_image(slug):
    if slug in {"salud", "medioambiente", "deportes"}:
        return f"news/images/{slug}.svg"
    return f"news/images/{slug if slug in CATEGORY_IMAGES else 'geopolitica'}.webp"


def articles_for(categories, mode):
    match = Q(categories__in=categories)
    if mode == UserPreference.CLASSIFICATION_AI:
        match = Q(llm_categories__in=categories)
    elif mode == UserPreference.CLASSIFICATION_BOTH:
        match |= Q(llm_categories__in=categories)
    return Article.objects.filter(
        match, feed__is_active=True, published_at__gte=retention_cutoff(), published_at__lte=timezone.now(),
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
    now = timezone.now()
    period = form.cleaned_data["period"]
    if period == "today":
        cutoff = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        articles = articles.filter(published_at__gte=cutoff)
    elif period:
        articles = articles.filter(published_at__gte=now - timedelta(days={"24h": 1, "3d": 3, "7d": 7}[period]))
    if text:
        if connection.vendor != "postgresql":
            form.add_error("q", "La búsqueda no está disponible en este entorno.")
            return form, articles.none(), text
        articles = search_articles(articles, text)
    return form, articles, text


def story_articles(articles, search_text=""):
    """Una cobertura que coincide con los filtros representa a cada acontecimiento."""
    fields = (["-relevance"] if search_text else []) + ["-published_at", "-pk"]
    representative = articles.filter(
        story_id=OuterRef("story_id"), feed__allow_ai_grouping=True,
    ).order_by(*fields).values("pk")[:1]
    return articles.filter(
        ~Q(story__grouping_version=GROUPING_VERSION) | Q(feed__allow_ai_grouping=False)
        | Q(pk=Subquery(representative))
    )


def add_coverages(rows):
    story_ids = {article.story_id for article in rows if article.has_verified_story}
    grouped = {}
    coverages = Article.objects.filter(
        story_id__in=story_ids, feed__is_active=True, feed__allow_ai_grouping=True,
        published_at__gte=retention_cutoff(), published_at__lte=timezone.now(),
    ).select_related("feed__source").order_by("feed__source__name", "-published_at", "-pk")
    for coverage in coverages:
        grouped.setdefault(coverage.story_id, []).append(coverage)
    for article in rows:
        article.coverages = grouped.get(article.story_id, [article]) if article.has_verified_story else [article]
        article.coverage_sources = sorted({item.feed.source.name for item in article.coverages})


def article_batch(request, articles, context, search_text, sort=""):
    ranked = bool(search_text) and sort != "recent"
    if ranked:
        articles = articles.annotate(relevance=Cast("relevance", FloatField()))
    if sort == "important":
        articles = articles.annotate(importance=Case(
            When(feed__allow_ai_grouping=True, story__grouping_version=GROUPING_VERSION,
                 story__importance_score__isnull=False, then="story__importance_score"),
            default=Value(0), output_field=IntegerField(),
        ))
    fields = (["importance"] if sort == "important" else []) + (["relevance"] if ranked else []) + ["published_at", "pk"]
    articles = articles.select_related("feed__source", "story").order_by(*[f"-{field}" for field in fields])
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
            if sort == "important" and (type(values[0]) is not int or not 0 <= values[0] <= 5):
                raise ValueError
            if ranked and (type(values[-3]) not in (int, float) or not 0 <= values[-3] < float("inf")):
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
