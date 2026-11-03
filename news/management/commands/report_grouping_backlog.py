"""Cuenta pendientes por fecha de publicación sin modificar noticias ni llamar a IA."""

import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from news.models import GROUPING_VERSION, Article, NewsBriefingItem
from news.ingestion import AI_EXCLUDED_SOURCES
from news.retention import RETENTION_DAYS
from news.briefings import current_briefing_items
from news.browsing import articles_for, story_articles, with_importance
from news.models import Category, UserPreference


class Command(BaseCommand):
    help = "Informa la antigüedad de las noticias pendientes de agrupamiento (sólo lectura)."

    def handle(self, *args, **options):
        now = timezone.now()
        day = now - timedelta(hours=24)
        two_days = now - timedelta(hours=48)
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
            pending = Article.objects.filter(
                feed__is_active=True,
                feed__allow_ai_grouping=True,
                published_at__gte=now - timedelta(days=RETENTION_DAYS),
                published_at__lte=now,
            ).exclude(feed__source__name__in=AI_EXCLUDED_SOURCES).filter(
                Q(story__isnull=True) | ~Q(story__grouping_version=GROUPING_VERSION))
            counts = pending.aggregate(
                total=Count("pk"),
                up_to_24h=Count("pk", filter=Q(published_at__gte=day)),
                over_24h_up_to_48h=Count("pk", filter=Q(published_at__lt=day, published_at__gte=two_days)),
                over_48h=Count("pk", filter=Q(published_at__lt=two_days)),
                legacy_groups=Count("pk", filter=Q(story__isnull=False)),
                oldest=Min("published_at"),
                newest=Max("published_at"),
            )
            sports = Article.objects.filter(
                Q(categories__slug="deportes") | Q(llm_categories__slug="deportes"),
                feed__is_active=True, published_at__gte=day, published_at__lte=now,
            )
            sports_sources = list(sports.values(
                "feed__source__name", "feed__name", "feed__allow_ai_briefing", "feed__show_summary",
            ).annotate(articles=Count("pk", distinct=True)).order_by("feed__source__name", "feed__name"))
            sports_items = NewsBriefingItem.objects.filter(
                category__slug="deportes", briefing__status="ready", briefing__generated_at__gte=day,
            ).count()
            categories = list(Category.objects.filter(slug="argentina"))
            alignment = []
            for category in categories:
                for mode, _ in UserPreference.CLASSIFICATION_CHOICES:
                    item = current_briefing_items(now, categories).get(category.pk)
                    reference = item.articles.first() if item else None
                    candidates = articles_for([category]).filter(published_at__gte=day)
                    for period, rows in (("24h", candidates), ("today", candidates.filter(
                        published_at__gte=timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0),
                    ))):
                        winner = with_importance(story_articles(rows)).order_by("-importance", "-published_at", "-pk").first()
                        alignment.append({"category": category.slug, "mode": mode, "period": period,
                            "summary_reference_id": reference.pk if reference else None,
                            "summary_generated_at": item.briefing.generated_at if item else None,
                            "winner_id": winner.pk if winner else None,
                            "winner_score": winner.importance if winner else None,
                            "same_story": bool(reference and winner and (reference.pk == winner.pk or
                                reference.has_verified_story and winner.has_verified_story and reference.story_id == winner.story_id)),
                            "winner_allows_summary": winner.feed.allow_ai_briefing if winner else None})
        self.stdout.write(json.dumps({"measured_at": now, "retention_days": RETENTION_DAYS, **counts,
                                      "sports_last_24h_sources": sports_sources,
                                      "sports_briefing_items_generated_last_24h": sports_items,
                                      "argentina_summary_alignment": alignment},
                                     ensure_ascii=False, default=str))
