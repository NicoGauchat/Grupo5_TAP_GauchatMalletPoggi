"""Clasifica por IA las noticias recientes aún pendientes."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from news.llm_classification import BATCH_SIZE, CATEGORY_DESCRIPTIONS, MODEL, ClassificationError, classify_batch
from news.ingestion import AI_EXCLUDED_SOURCES
from news.models import Article, Category
from news.retention import retention_cutoff


class Command(BaseCommand):
    help = "Clasifica titulares recientes con Gemini, sin cambiar las categorías por reglas."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Máximo de noticias por ejecución (1 a 100)")

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= 100:
            raise CommandError("--limit debe estar entre 1 y 100")
        categories = dict(Category.objects.filter(slug__in=CATEGORY_DESCRIPTIONS).values_list("slug", "id"))
        pending = list(
            Article.objects.filter(
                llm_classified_at__isnull=True, published_at__gte=retention_cutoff(),
                feed__is_active=True,
            ).exclude(feed__source__name__in=AI_EXCLUDED_SOURCES).select_related("feed__source").order_by("-published_at", "-id")[:limit]
        )
        if not pending:
            self.stdout.write("No hay noticias pendientes de clasificación por IA.")
            return

        processed = 0
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start:start + BATCH_SIZE]
            try:
                predictions = classify_batch(batch, categories)
            except ClassificationError as error:
                raise CommandError(
                    f"Se clasificaron {processed} noticias; el resto queda pendiente. {error}"
                ) from error
            with transaction.atomic():
                classified_at = timezone.now()
                for article in batch:
                    article.llm_categories.set([categories[slug] for slug in predictions[article.pk]])
                    article.llm_classified_at = classified_at
                    article.llm_model = MODEL
                    article.save(update_fields=["llm_classified_at", "llm_model"])
            processed += len(batch)
        self.stdout.write(f"Se clasificaron {processed} noticias por IA con {MODEL}.")
