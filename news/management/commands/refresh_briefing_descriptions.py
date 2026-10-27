"""Activa opcionalmente y actualiza la entradilla RSS de la fuente revisada."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from news.ingestion import ELDIARIO_DESCRIPTION_FEED, ELDIARIO_LICENSE, IngestionError, ingest_feed
from news.models import Article, Feed


class Command(BaseCommand):
    help = "Actualiza descripciones RSS revisadas de elDiario.es, sin descargar páginas de noticias."

    def add_arguments(self, parser):
        parser.add_argument("--enable-reviewed", action="store_true",
                            help="Habilitar síntesis y descripción sólo en el feed revisado de elDiario.es.")

    def handle(self, *args, **options):
        feeds = Feed.objects.filter(
            is_active=True, url=ELDIARIO_DESCRIPTION_FEED,
            source__name="elDiario.es", source__license_url=ELDIARIO_LICENSE,
        ).select_related("source")
        if not options["enable_reviewed"]:
            feeds = feeds.filter(show_summary=True, allow_ai_briefing=True)
        feeds = list(feeds)
        if not feeds:
            raise CommandError("No hay un feed activo revisado con su atribución y licencia configuradas.")
        for feed in feeds:
            if options["enable_reviewed"]:
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
