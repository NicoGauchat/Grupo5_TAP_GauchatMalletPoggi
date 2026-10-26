"""Selección de resúmenes vigentes y estados visibles de la presentación."""

from datetime import timedelta

from django.db.models import Q

from .models import Article, Category, NewsBriefing, NewsBriefingItem


def briefing_context(now, categories=()):
    categories = list(categories)
    if not categories:
        return {"category_briefings": [], "has_briefing_items": False}
    cutoff = now - timedelta(hours=24)
    eligible = Article.objects.filter(
        feed__is_active=True, feed__allow_ai_briefing=True, published_at__gte=cutoff, published_at__lte=now,
    )
    available = set(Category.objects.filter(
        Q(articles__in=eligible) | Q(llm_articles__in=eligible), pk__in=[category.pk for category in categories],
    ).values_list("pk", flat=True))
    items = NewsBriefingItem.objects.filter(
        category__in=categories, briefing__status="ready", briefing__generated_at__gte=cutoff,
    ).exclude(articles__published_at__lt=cutoff).exclude(articles__published_at__gt=now).exclude(
        articles__published_at__isnull=True,
    ).exclude(articles__feed__is_active=False).exclude(articles__feed__allow_ai_briefing=False).select_related("briefing").prefetch_related(
        "articles__feed__source", "articles__categories", "articles__llm_categories",
    ).order_by("-briefing__generated_at", "-briefing_id", "position")
    latest = {}
    for item in items:
        references = list(item.articles.all())
        if len(references) == 1 and item.category_id in {
            category.pk for category in [*references[0].categories.all(), *references[0].llm_categories.all()]
        }:
            latest.setdefault(item.category_id, item)
    attempt = NewsBriefing.objects.filter(generated_at__gte=cutoff).first()
    rows = []
    for category in categories:
        item = latest.get(category.pk)
        state = "ready" if item else "no_articles" if category.pk not in available else (
            "error" if attempt and attempt.status == "error" else "pending"
        )
        rows.append({"category": category, "item": item, "state": state,
                     "update_failed": bool(item and attempt and attempt.status == "error")})
    return {"category_briefings": rows, "has_briefing_items": any(row["item"] for row in rows)}


def valid_briefings(now):
    cutoff = now - timedelta(hours=24)
    return NewsBriefing.objects.filter(generated_at__gte=cutoff).exclude(status="error").exclude(
        items__articles__published_at__lt=cutoff,
    ).exclude(items__articles__published_at__gt=now).exclude(
        items__articles__published_at__isnull=True, status="ready",
    ).exclude(items__articles__feed__allow_ai_briefing=False).exclude(
        items__articles__feed__is_active=False,
    )
