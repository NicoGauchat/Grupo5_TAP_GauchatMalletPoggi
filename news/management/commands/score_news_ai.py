"""Evalúa acontecimientos pendientes o con nuevas coberturas autorizadas."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from news.llm_classification import MODEL
from news.ingestion import AI_EXCLUDED_SOURCES
from news.llm_importance import ImportanceError, score_stories
from news.models import GROUPING_VERSION, Article, Story
from news.retention import retention_cutoff
from news.ollama import batch_size as inference_batch_size


class Command(BaseCommand):
    help = "Asigna importancia pública general (1–5) a los acontecimientos con Gemini."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--force", action="store_true", help="Reevaluar también acontecimientos ya puntuados.")

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 500:
            raise CommandError("--limit debe estar entre 1 y 500.")
        now = timezone.now()
        allowed = Q(articles__feed__is_active=True, articles__feed__allow_ai_grouping=True,
                    articles__published_at__gte=retention_cutoff(), articles__published_at__lte=now) & ~Q(
                        articles__feed__source__name__in=AI_EXCLUDED_SOURCES)
        stories = Story.objects.filter(grouping_version=GROUPING_VERSION).annotate(
            latest_coverage=Max("articles__fetched_at", filter=allowed),
        ).filter(latest_coverage__isnull=False)
        if not options["force"]:
            stories = stories.filter(Q(importance_scored_at__isnull=True) | Q(importance_scored_at__lt=F("latest_coverage")))
        ids = list(stories.order_by("-latest_coverage", "-pk").values_list("pk", flat=True)[:options["limit"]])
        processed = 0
        batch_size = inference_batch_size()
        for start in range(0, len(ids), batch_size):
            batch = {pk: [] for pk in ids[start:start + batch_size]}
            sources = {pk: set() for pk in batch}
            for article in Article.objects.filter(
                story_id__in=batch, feed__is_active=True, feed__allow_ai_grouping=True,
                published_at__gte=retention_cutoff(), published_at__lte=now,
            ).exclude(feed__source__name__in=AI_EXCLUDED_SOURCES).select_related("feed__source").order_by("-published_at", "-pk"):
                seen = sources[article.story_id]
                if article.feed.source_id not in seen and len(seen) < 3:
                    batch[article.story_id].append(article)
                    seen.add(article.feed.source_id)
            batch = {pk: articles for pk, articles in batch.items() if articles}
            if not batch:
                continue
            assessed_at = timezone.now()
            try:
                scores = score_stories(batch)
            except ImportanceError as error:
                raise CommandError(f"Se evaluaron {processed} acontecimientos. {error}") from error
            with transaction.atomic():
                for story in Story.objects.select_for_update().filter(pk__in=batch).order_by("pk"):
                    if story.importance_scored_at and story.importance_scored_at > assessed_at:
                        continue
                    result = scores[story.pk]
                    story.importance_score, story.importance_reason = result["score"], result["reason"]
                    story.importance_scored_at, story.importance_model = assessed_at, getattr(scores, "model", MODEL)
                    story.save(update_fields=["importance_score", "importance_reason", "importance_scored_at", "importance_model"])
                    processed += 1
        self.stdout.write(f"Se evaluaron {processed} acontecimientos por importancia general.")
