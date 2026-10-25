"""Asocia titulares pendientes a acontecimientos sin modificar los artículos originales."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from news.llm_classification import MODEL
from news.llm_grouping import GroupingError, group_articles
from news.models import Article, Story
from news.retention import retention_cutoff


BATCH_SIZE = 30
MAX_CANDIDATES = 500


class Command(BaseCommand):
    help = "Agrupa coberturas del mismo acontecimiento mediante Gemini."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Máximo de noticias pendientes (1 a 500).")

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= 500:
            raise CommandError("--limit debe estar entre 1 y 500.")
        eligible = Article.objects.filter(
            feed__is_active=True, feed__allow_ai_grouping=True, published_at__gte=retention_cutoff(), published_at__lte=timezone.now(),
        ).select_related("feed__source")
        pending = list(eligible.filter(story__isnull=True).order_by("published_at", "pk")[:limit])
        processed = 0
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start:start + BATCH_SIZE]
            representatives = {}
            for article in eligible.filter(story__isnull=False).order_by("-published_at", "-pk").iterator():
                representatives.setdefault(article.story_id, article)
            try:
                candidates = list(representatives.values())
                remaining, groups, new_groups = batch, [], []
                for offset in range(0, max(1, len(candidates)), MAX_CANDIDATES):
                    result = group_articles(remaining, candidates[offset:offset + MAX_CANDIDATES])
                    groups.extend(row for row in result if row["story_id"])
                    new_groups = [row for row in result if not row["story_id"]]
                    unmatched = {pk for row in new_groups for pk in row["article_ids"]}
                    remaining = [article for article in remaining if article.pk in unmatched]
                    if not remaining:
                        break
                groups.extend(new_groups)
            except GroupingError as error:
                raise CommandError(f"Se agruparon {processed} noticias. {error}") from error
            with transaction.atomic():
                stories = list(Story.objects.select_for_update().filter(pk__in=representatives).order_by("pk"))
                locked = list(eligible.select_for_update(of=("self",)).filter(
                    pk__in=[article.pk for article in batch], story__isnull=True,
                ))
                if len(locked) != len(batch) or len(stories) != len(representatives):
                    raise CommandError("Los datos cambiaron durante el agrupamiento; volvé a ejecutar el comando.")
                for group in groups:
                    story_id = group["story_id"] or Story.objects.create(llm_model=MODEL).pk
                    Article.objects.filter(pk__in=group["article_ids"]).update(story_id=story_id)
                    Story.objects.filter(pk=story_id).update(importance_scored_at=None)
            processed += len(batch)
        remaining = eligible.filter(story__isnull=True).count()
        self.stdout.write(f"Se agruparon {processed} noticias; quedan {remaining} pendientes.")
