"""Asocia titulares pendientes a acontecimientos sin modificar los artículos originales."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Case, Q, Value, When
from django.utils import timezone

from news.llm_classification import MODEL
from news.ingestion import AI_EXCLUDED_SOURCES
from news.llm_grouping import GroupingError, group_articles, metadata
from news.models import GROUPING_VERSION, Article, Story
from news.retention import retention_cutoff
from news.ollama import enabled as local_first
from news import ollama


BATCH_SIZE = 10
MAX_CANDIDATES = 100


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
        ).exclude(feed__source__name__in=AI_EXCLUDED_SOURCES).select_related("feed__source")
        needs_review = Q(story__isnull=True) | ~Q(story__grouping_version=GROUPING_VERSION)
        pending = list(eligible.filter(needs_review).annotate(
            review_priority=Case(When(story__isnull=False, then=Value(0)), default=Value(1)),
        ).order_by("review_priority", "-published_at", "-pk")[:limit])
        processed = 0
        candidate_limit = MAX_CANDIDATES
        batch_size = 3 if local_first() else BATCH_SIZE
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            representatives = {}
            for article in eligible.filter(story__grouping_version=GROUPING_VERSION).order_by("pk").iterator():
                representatives.setdefault(article.story_id, article)
            try:
                candidates = list(representatives.values())
                allow_local = True
                if local_first():
                    try:
                        candidates = ollama.shortlist_candidates(batch, candidates)
                        representatives = {article.story_id: article for article in candidates}
                    except ollama.LocalModelError as error:
                        self.stderr.write(self.style.WARNING(f"No se pudo recuperar candidatos locales; se intenta la API. {error}"))
                        allow_local = False
                groups, candidate_limit = self.propose_batch(batch, candidates, candidate_limit, allow_local=allow_local)
            except GroupingError as error:
                raise CommandError(f"Se agruparon {processed} noticias. {error}") from error
            with transaction.atomic():
                stories = list(Story.objects.select_for_update().filter(pk__in=representatives).order_by("pk"))
                locked = list(eligible.select_for_update(of=("self",)).filter(
                    pk__in=[article.pk for article in batch],
                ))
                def snapshot(rows):
                    return {article.pk: (article.story_id, metadata(article), article.feed_id) for article in rows}
                current_anchors = list(eligible.select_for_update(of=("self",)).filter(
                    pk__in=[article.pk for article in representatives.values()],
                    story__grouping_version=GROUPING_VERSION,
                ))
                if (snapshot(locked) != snapshot(batch) or len(stories) != len(representatives)
                    or snapshot(current_anchors) != snapshot(representatives.values())):
                    raise CommandError("Los datos cambiaron durante el agrupamiento; volvé a ejecutar el comando.")
                for group in groups:
                    story_id = group["story_id"] or Story.objects.create(llm_model=group["_model"]).pk
                    Article.objects.filter(pk__in=group["article_ids"]).update(story_id=story_id)
                    Story.objects.filter(pk=story_id).update(
                        importance_score=None, importance_reason="", importance_scored_at=None, importance_model="",
                    )
            processed += len(batch)
        remaining = eligible.filter(needs_review).count()
        legacy = eligible.filter(needs_review, story__isnull=False).count()
        self.stdout.write(f"Se agruparon {processed} noticias; quedan {remaining} pendientes ({legacy} de grupos anteriores).")

    def propose_batch(self, batch, candidates, candidate_limit, *, allow_local=True):
        while True:
            try:
                remaining, groups, new_groups = batch, [], []
                for offset in range(0, max(1, len(candidates)), candidate_limit):
                    kwargs = {} if allow_local else {"allow_local": False}
                    result = group_articles(remaining, candidates[offset:offset + candidate_limit], **kwargs)
                    result = [dict(row, _model=getattr(result, "model", MODEL)) for row in result]
                    groups.extend(row for row in result if row["story_id"])
                    new_groups = [row for row in result if not row["story_id"]]
                    unmatched = {pk for row in new_groups for pk in row["article_ids"]}
                    remaining = [article for article in remaining if article.pk in unmatched]
                    if not remaining:
                        break
                return groups + new_groups, candidate_limit
            except GroupingError as error:
                if not error.reduce_candidates or candidate_limit <= 1 or len(candidates) <= 1:
                    raise
                candidate_limit = max(1, min(candidate_limit, len(candidates)) // 2)
                self.stderr.write(self.style.WARNING(
                    f"Agrupamiento: petición demasiado grande; se repite el lote con bloques de {candidate_limit} candidatos."
                ))
