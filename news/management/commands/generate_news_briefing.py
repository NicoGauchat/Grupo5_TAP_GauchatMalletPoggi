"""Genera una presentación común con titulares publicados en las últimas 24 horas."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from news.llm_briefing import BriefingError, summarize_articles
from news.models import Article, NewsBriefing, NewsBriefingItem
from news.retention import RETENTION_DAYS


MAX_ARTICLES = 250


class Command(BaseCommand):
    help = "Genera o actualiza la presentación a partir de titulares de las últimas 24 horas."

    def handle(self, *args, **options):
        generated_at = timezone.now()
        window_start = generated_at - timedelta(hours=24)
        articles = list(
            Article.objects.filter(
                feed__is_active=True,
                feed__allow_ai_briefing=True,
                published_at__gte=window_start,
                published_at__lte=generated_at,
            ).select_related("feed__source").order_by("-published_at", "-id")
        )

        if len(articles) > MAX_ARTICLES:
            self.stdout.write(self.style.WARNING(
                f"Hay {len(articles)} titulares recientes; se supera el límite seguro de "
                f"{MAX_ARTICLES}. Se conserva la última presentación."
            ))
            return

        try:
            items = summarize_articles(articles)
        except BriefingError as error:
            self.stdout.write(self.style.WARNING(
                f"No se actualizó la presentación; se conserva la última válida. {error}"
            ))
            return

        with transaction.atomic():
            briefing = NewsBriefing.objects.create(
                window_start=window_start,
                article_count=len(articles),
            )
            articles_by_id = {article.pk: article for article in articles}
            for position, item in enumerate(items, start=1):
                briefing_item = NewsBriefingItem.objects.create(
                    briefing=briefing,
                    position=position,
                    text=item["text"],
                )
                briefing_item.articles.set(articles_by_id[pk] for pk in item["article_ids"])

            NewsBriefing.objects.filter(
                generated_at__lt=generated_at - timedelta(days=RETENTION_DAYS),
            ).delete()

        if not articles:
            self.stdout.write("No hubo noticias publicadas en las últimas 24 horas; se guardó ese estado.")
        else:
            self.stdout.write(
                f"Presentación actualizada: {len(items)} puntos sobre "
                f"{len(articles)} titulares de las últimas 24 horas."
            )
