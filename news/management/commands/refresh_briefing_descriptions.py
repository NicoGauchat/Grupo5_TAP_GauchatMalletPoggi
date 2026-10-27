"""Activa opcionalmente y actualiza la entradilla RSS de la fuente revisada."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from news.ingestion import AI_EXCLUDED_SOURCES, ELDIARIO_DESCRIPTION_FEED, ELDIARIO_LICENSE, LOSANDES_DESCRIPTION_FEEDS, NASA_DESCRIPTION_FEED, NASA_USAGE_POLICY, IngestionError, ingest_feed
from news.models import Article, Feed


class Command(BaseCommand):
    help = "Actualiza descripciones RSS revisadas de elDiario.es, NASA o Los Andes, sin descargar páginas de noticias."

    def add_arguments(self, parser):
        parser.add_argument("--enable-reviewed", action="store_true",
                            help="Habilitar síntesis y descripción sólo en las fuentes revisadas seleccionadas.")
        parser.add_argument("--source", choices=["eldiario", "nasa", "losandes", "all"], default="eldiario")

    def handle(self, *args, **options):
        reviewed = Q(pk__in=[])
        if options["source"] in {"eldiario", "all"}:
            reviewed |= Q(url=ELDIARIO_DESCRIPTION_FEED, source__name="elDiario.es", source__license_url=ELDIARIO_LICENSE)
        if options["source"] in {"nasa", "all"}:
            reviewed |= Q(url=NASA_DESCRIPTION_FEED, source__name="NASA",
                          source__license_url__in=["", NASA_USAGE_POLICY] if options["enable_reviewed"] else [NASA_USAGE_POLICY])
        if options["source"] in {"losandes", "all"}:
            reviewed |= Q(url__in=LOSANDES_DESCRIPTION_FEEDS, source__name="Los Andes")
        feeds = Feed.objects.filter(reviewed, is_active=True).select_related("source")
        if not options["enable_reviewed"]:
            feeds = feeds.filter(show_summary=True, allow_ai_briefing=True)
        feeds = list(feeds)
        if not feeds:
            raise CommandError("No hay un feed activo revisado con su atribución y licencia configuradas.")
        if options["source"] == "all" and options["enable_reviewed"]:
            disabled = Feed.objects.filter(source__name__in=AI_EXCLUDED_SOURCES).update(
                show_summary=False, allow_ai_briefing=False, allow_ai_grouping=False,
            )
            self.stdout.write(f"Política revisada: {disabled} feeds con oposición expresa excluidos de IA; RSS conservado.")
        for feed in feeds:
            if options["enable_reviewed"]:
                if feed.url == NASA_DESCRIPTION_FEED and not feed.source.license_url:
                    feed.source.license_url = NASA_USAGE_POLICY
                    feed.source.save(update_fields=["license_url"])
                feed.show_summary = feed.allow_ai_briefing = True
                feed.save(update_fields=["show_summary", "allow_ai_briefing"])
            try:
                result = ingest_feed(feed, force_download=True)
            except IngestionError as error:
                raise CommandError(f"No se pudo actualizar el RSS revisado: {error}") from error
            now = timezone.now()
            recent = Article.objects.filter(feed=feed, published_at__gte=now - timedelta(hours=24),
                                             published_at__lte=now).exclude(summary="").count()
            self.stdout.write(
                f"RSS revisado actualizado: {result.created} noticias nuevas; "
                f"{result.duplicates} existentes revisadas; {recent} entradillas disponibles en las últimas 24 horas."
            )
