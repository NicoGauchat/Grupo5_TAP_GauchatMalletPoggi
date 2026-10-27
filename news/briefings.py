"""Selección de resúmenes vigentes y estados visibles de la presentación."""

from datetime import timedelta

from django.db.models import Q

from .models import Article, Category, NewsBriefing, NewsBriefingItem
from .browsing import add_coverages, article_illustration


def current_briefing_items(now, categories):
    """Última selección válida de cada categoría, aunque otra categoría haya vencido."""
    cutoff = now - timedelta(hours=24)
    items = NewsBriefingItem.objects.filter(
        category__in=categories, briefing__status="ready", briefing__generated_at__gte=cutoff,
    ).exclude(articles__published_at__lt=cutoff).exclude(articles__published_at__gt=now).exclude(
        articles__published_at__isnull=True,
    ).exclude(articles__feed__is_active=False).exclude(articles__feed__allow_ai_briefing=False).select_related("briefing").prefetch_related(
        "articles__feed__source", "articles__story", "articles__categories", "articles__llm_categories",
    ).order_by("-briefing__generated_at", "-briefing_id", "position")
    latest = {}
    for item in items:
        references = list(item.articles.all())
        if len(references) == 1 and item.category_id in {
            category.pk for category in [*references[0].categories.all(), *references[0].llm_categories.all()]
        }:
            latest.setdefault(item.category_id, item)
    return latest


def briefing_context(now, categories=()):
    categories = list(categories)
    if not categories:
        return {"category_briefings": [], "has_briefing_items": False, "has_missing_briefings": False}
    cutoff = now - timedelta(hours=24)
    eligible = Article.objects.filter(
        feed__is_active=True, feed__allow_ai_briefing=True, published_at__gte=cutoff, published_at__lte=now,
    )
    available = set(Category.objects.filter(
        Q(articles__in=eligible) | Q(llm_articles__in=eligible), pk__in=[category.pk for category in categories],
    ).values_list("pk", flat=True))
    latest = current_briefing_items(now, categories)
    attempt = NewsBriefing.objects.filter(generated_at__gte=cutoff).first()
    references = {category_id: list(item.articles.all())[0] for category_id, item in latest.items()}
    add_coverages(list(references.values()), cutoff=cutoff, now=now)
    rows = []
    for category in categories:
        item = latest.get(category.pk)
        state = "ready" if item else "no_articles" if category.pk not in available else (
            "error" if attempt and attempt.status == "error" else "pending"
        )
        reference = references.get(category.pk)
        sources = {}
        image_article = None
        if reference:
            sources[reference.feed.source_id] = reference
            for coverage in reference.coverages:
                sources.setdefault(coverage.feed.source_id, coverage)
            candidates = [reference]
            if reference.has_verified_story:
                candidates.extend(sorted(
                    (coverage for coverage in reference.coverages if coverage.pk != reference.pk),
                    key=lambda coverage: (coverage.published_at, coverage.pk), reverse=True,
                ))
            image_article = next((article for article in candidates
                                  if article.feed.is_active and article.feed.show_images and article.image_url), None)
        rows.append({"category": category, "item": item, "state": state,
                     "sources": sorted(sources.values(), key=lambda article: article.feed.source.name.casefold()),
                     "source_count": len(sources), "reference_id": reference.pk if reference else None,
                     "image_article": image_article,
                     "fallback_image": article_illustration(reference, category.slug) if reference else None,
                     "update_failed": bool(item and attempt and attempt.status == "error")})
    return {"category_briefings": rows, "has_briefing_items": any(row["item"] for row in rows),
            "has_missing_briefings": any(not row["item"] for row in rows)}


def valid_briefings(now):
    cutoff = now - timedelta(hours=24)
    return NewsBriefing.objects.filter(generated_at__gte=cutoff).exclude(status="error").exclude(
        items__articles__published_at__lt=cutoff,
    ).exclude(items__articles__published_at__gt=now).exclude(
        items__articles__published_at__isnull=True, status="ready",
    ).exclude(items__articles__feed__allow_ai_briefing=False).exclude(
        items__articles__feed__is_active=False,
    )
