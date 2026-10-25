"""Selección de resúmenes vigentes y estados visibles de la presentación."""

import os
from datetime import timedelta

from .models import Article, Feed, NewsBriefing


def valid_briefings(now):
    cutoff = now - timedelta(hours=24)
    return NewsBriefing.objects.filter(generated_at__gte=cutoff).exclude(status="error").exclude(
        items__articles__published_at__lt=cutoff,
    ).exclude(items__articles__published_at__gt=now).exclude(
        items__articles__published_at__isnull=True, status="ready",
    ).exclude(items__articles__feed__allow_ai_briefing=False).exclude(
        items__articles__feed__is_active=False,
    )


def briefing_context(now):
    briefing = valid_briefings(now).prefetch_related("items__articles__feed__source").first()
    latest = NewsBriefing.objects.filter(generated_at__gte=now - timedelta(hours=24)).first()
    feeds = Feed.objects.filter(is_active=True, allow_ai_briefing=True)
    if not feeds.exists():
        state = "no_feeds"
        briefing = None
    elif not os.environ.get("GEMINI_API_KEY", "").strip() and not briefing:
        state = "missing_key"
    elif latest and latest.status == "error":
        state = "error"
    elif briefing:
        state = "ready" if briefing.items.exists() else ("no_highlights" if briefing.article_count else "no_articles")
    elif not Article.objects.filter(
        feed__in=feeds, published_at__gte=now - timedelta(hours=24), published_at__lte=now,
    ).exists():
        state = "no_articles"
    else:
        state = "pending"
    return {"briefing": briefing, "briefing_state": state}
