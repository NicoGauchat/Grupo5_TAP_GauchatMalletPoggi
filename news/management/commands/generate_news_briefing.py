"""Genera una presentación común con titulares publicados en las últimas 24 horas."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from news.briefings import valid_briefings
from news.llm_briefing import BriefingError, summarize_articles
from news.models import Article, Feed, NewsBriefing, NewsBriefingItem
from news.retention import RETENTION_DAYS


MAX_ARTICLES = 250


class Command(BaseCommand):
    help = "Genera o actualiza la presentación a partir de titulares de las últimas 24 horas."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerar aunque exista un resultado de las últimas dos horas")

    def handle(self, *args, **options):
        generated_at = timezone.now()
        window_start = generated_at - timedelta(hours=24)
        enabled = Feed.objects.filter(is_active=True, allow_ai_briefing=True).exists()
        cached = valid_briefings(generated_at).filter(generated_at__gte=generated_at - timedelta(hours=2))
        if enabled:
            cached = cached.exclude(error_code="no_feeds")
        else:
            cached = cached.filter(error_code="no_feeds")
        if not options["force"] and cached.exists():
            self.stdout.write("Se reutiliza la presentación de las últimas dos horas.")
            return

        eligible = Article.objects.filter(
            feed__is_active=True, feed__allow_ai_briefing=True,
            published_at__gte=window_start, published_at__lte=generated_at,
        ).select_related("feed__source").order_by("-published_at", "-id")
        articles = list(eligible[:MAX_ARTICLES + 1])
        if len(articles) > MAX_ARTICLES:
            articles = articles[:MAX_ARTICLES]
            self.stdout.write(self.style.WARNING(
                f"Se analizarán los {MAX_ARTICLES} titulares más recientes; hay más noticias en la ventana."
            ))

        status, error_code = "ready", ""
        try:
            items = summarize_articles(articles)
            if not items:
                status = "empty"
                error_code = "no_feeds" if not enabled else "no_highlights" if articles else "no_articles"
        except BriefingError as error:
            items, status, error_code = [], "error", error.code
            self.stdout.write(self.style.WARNING(
                f"No se actualizó la presentación; se conserva la última válida. {error}"
            ))

        with transaction.atomic():
            briefing = NewsBriefing.objects.create(
                window_start=window_start,
                article_count=len(articles),
                status=status,
                error_code=error_code,
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

        if status == "error":
            return
        if not enabled:
            self.stdout.write("No hay fuentes habilitadas para la presentación.")
        elif not articles:
            self.stdout.write("No hubo noticias publicadas en las últimas 24 horas; se guardó ese estado.")
        else:
            self.stdout.write(
                f"Presentación actualizada: {len(items)} puntos sobre "
                f"{len(articles)} titulares de las últimas 24 horas."
            )
