"""Genera una presentación común con titulares publicados en las últimas 24 horas."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from news.briefings import current_briefing_items, valid_briefings
from news.ingestion import AI_EXCLUDED_SOURCES
from news.llm_briefing import BriefingError, summarize_articles
from news.models import Article, Category, Feed, NewsBriefing, NewsBriefingItem
from news.retention import RETENTION_DAYS


MAX_ARTICLES = 250


class Command(BaseCommand):
    help = "Genera una síntesis IA por categoría con titulares autorizados de las últimas 24 horas."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerar aunque exista un resultado de las últimas dos horas")

    def handle(self, *args, **options):
        generated_at = timezone.now()
        window_start = generated_at - timedelta(hours=24)
        enabled = Feed.objects.filter(is_active=True, allow_ai_briefing=True).exists()
        eligible = Article.objects.filter(
            feed__is_active=True, feed__allow_ai_briefing=True,
            published_at__gte=window_start, published_at__lte=generated_at,
        ).exclude(feed__source__name__in=AI_EXCLUDED_SOURCES).select_related("feed__source").order_by("-published_at", "-id")
        categories = list(Category.objects.filter(
            Q(articles__in=eligible) | Q(llm_articles__in=eligible),
        ).distinct())
        cached = valid_briefings(generated_at).filter(generated_at__gte=generated_at - timedelta(hours=2))
        if enabled:
            cached = cached.exclude(error_code="no_feeds")
        else:
            cached = cached.filter(error_code="no_feeds")
        if not options["force"]:
            expected = {category.pk for category in categories}
            for previous in cached.prefetch_related("items__articles__categories", "items__articles__llm_categories"):
                stored = set()
                for item in previous.items.all():
                    references = list(item.articles.all())
                    if len(references) == 1 and item.category_id in {
                        category.pk for category in [*references[0].categories.all(), *references[0].llm_categories.all()]
                    }:
                        stored.add(item.category_id)
                if (previous.status == "ready" and stored == expected) or (previous.status == "empty" and not expected):
                    self.stdout.write("Se reutiliza la presentación de las últimas dos horas.")
                    return

        previous_items = current_briefing_items(generated_at, categories)
        previous_selection = {
            category.slug: list(previous_items[category.pk].articles.all())[0].pk
            for category in categories if category.pk in previous_items
        }
        selected_ids = set(previous_selection.values())
        per_category = max(1, MAX_ARTICLES // max(1, len(categories)))
        for category in categories:
            previous_id = previous_selection.get(category.slug)
            selected_ids.update(eligible.filter(
                Q(categories=category) | Q(llm_categories=category),
            ).exclude(pk=previous_id).distinct().values_list("pk", flat=True)[
                :per_category - (1 if previous_id is not None else 0)
            ])
        articles = list(eligible.filter(pk__in=selected_ids).prefetch_related("categories", "llm_categories"))

        status, error_code = "ready", ""
        try:
            items = summarize_articles(articles, previous_selection=previous_selection)
            if not items:
                status = "empty"
                error_code = "no_feeds" if not enabled else "no_articles"
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
            categories_by_slug = {category.slug: category for category in categories}
            for position, item in enumerate(items, start=1):
                briefing_item = NewsBriefingItem.objects.create(
                    briefing=briefing,
                    category=categories_by_slug[item["category_slug"]],
                    position=position,
                    text=item["text"],
                )
                briefing_item.articles.set(articles_by_id[pk] for pk in item["article_ids"])

            NewsBriefing.objects.filter(
                generated_at__lt=generated_at - timedelta(days=RETENTION_DAYS),
            ).delete()

        if status == "error":
            raise CommandError(f"Falló el resumen IA ({error_code}); se guardó el intento y se conserva la última síntesis vigente.")
        if not enabled:
            self.stdout.write("No hay fuentes habilitadas para la presentación.")
        elif not articles:
            self.stdout.write("No hubo noticias publicadas en las últimas 24 horas; se guardó ese estado.")
        else:
            retained = sum(previous_selection.get(item["category_slug"]) == item["article_ids"][0] for item in items)
            self.stdout.write(
                f"Presentación actualizada: {len(items)} puntos sobre "
                f"{len(articles)} titulares de las últimas 24 horas."
                f" Modelo: {getattr(items, 'model', 'no disponible')}."
            )
            self.stdout.write(
                f"Selección: {retained} referencias conservadas de {len(previous_selection)} anteriores vigentes."
            )
            self.stdout.write(f"Síntesis con entradilla RSS autorizada: {getattr(items, 'description_count', 0)}.")
