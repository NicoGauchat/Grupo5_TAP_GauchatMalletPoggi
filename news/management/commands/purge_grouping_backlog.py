"""Limpieza manual y acotada de pendientes antiguos, con simulación inicial."""

import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from news.models import GROUPING_VERSION, Article, SavedArticle
from news.retention import RETENTION_DAYS


class Command(BaseCommand):
    help = "Cuenta pendientes antiguos; --apply elimina sólo si coincide --expected-count."

    def add_arguments(self, parser):
        parser.add_argument("--published-before", required=True, help="Corte ISO 8601 con zona horaria, de al menos 48 horas.")
        parser.add_argument("--expected-count", type=int)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        try:
            cutoff = parse_datetime(options["published_before"])
        except ValueError:
            cutoff = None
        now = timezone.now()
        if cutoff is None or timezone.is_naive(cutoff) or cutoff > now - timedelta(hours=48):
            raise CommandError("El corte debe tener zona horaria y una antigüedad mínima de 48 horas.")
        expected = options["expected_count"]
        if options["apply"] and (expected is None or expected < 0):
            raise CommandError("Para eliminar se requiere --expected-count no negativo.")
        with transaction.atomic():
            pending = Article.objects.filter(
                feed__is_active=True, feed__allow_ai_grouping=True,
                published_at__gte=now - timedelta(days=RETENTION_DAYS), published_at__lt=cutoff,
            ).filter(Q(story__isnull=True) | ~Q(story__grouping_version=GROUPING_VERSION))
            # Bloquea sólo artículos; los grupos son opcionales y no se eliminan.
            ids = list(pending.select_for_update(of=("self",)).values_list("pk", flat=True))
            saved = SavedArticle.objects.filter(article_id__in=ids).count()
            self.stdout.write(json.dumps({"mode": "apply" if options["apply"] else "preview",
                                          "published_before": str(cutoff), "articles": len(ids),
                                          "saved_links": saved}))
            if not options["apply"]:
                return
            if len(ids) != expected:
                raise CommandError("El conteo cambió; no se eliminó ninguna noticia. Revisar la simulación.")
            _, deleted = Article.objects.filter(pk__in=ids).delete()
            self.stdout.write(json.dumps({"deleted_articles": deleted.get("news.Article", 0),
                                          "deleted_related_rows": deleted}))
