from django.core.management.base import BaseCommand, CommandError

from news.ingestion import IngestionError, ingest_feed
from news.models import Feed


class Command(BaseCommand):
    help = "Consulta los feeds RSS activos y guarda noticias sin duplicados exactos."

    def add_arguments(self, parser):
        parser.add_argument("--feed-id", type=int, help="Procesar un solo feed activo")
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Volver a descargar y reclasificar, aunque el feed no haya cambiado",
        )

    def handle(self, *args, **options):
        feeds = Feed.objects.filter(is_active=True).select_related("source")
        if options["feed_id"]:
            feeds = feeds.filter(pk=options["feed_id"])
        if not feeds.exists():
            raise CommandError("No se encontraron feeds activos.")

        errors = []
        successful = 0
        for feed in feeds:
            try:
                result = ingest_feed(feed, force_download=options["refresh"])
            except IngestionError as error:
                errors.append(f"{feed}: {error}")
                self.stderr.write(self.style.WARNING(errors[-1]))
                continue

            successful += 1
            if result.unchanged:
                self.stdout.write(f"{feed}: sin cambios (HTTP 304)")
            else:
                self.stdout.write(
                    f"{feed}: {result.created} nuevas, "
                    f"{result.duplicates} duplicadas, {result.skipped} omitidas"
                )

        if errors:
            raise CommandError(
                f"Fallaron {len(errors)} feed(s); {successful} consultados correctamente.",
                returncode=2 if successful else 1,
            )
