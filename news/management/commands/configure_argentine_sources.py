"""Aplica la selección explícita de medios argentinos revisada para el proyecto."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from news.ingestion import IngestionError, ingest_feed
from news.models import Category, Feed, Source


REVIEWED_FEEDS = (
    ("Cenital", "https://cenital.com/", "General", "https://cenital.com/feed/"),
    ("La Capital", "https://www.lacapital.com.ar/", "General", "https://www.lacapital.com.ar/rss/home.xml"),
    ("El Ciudadano", "https://elciudadanoweb.com/", "General", "https://elciudadanoweb.com/feed/"),
)


class Command(BaseCommand):
    help = "Simula la selección de tres medios argentinos y retiro de EL PAÍS; --apply la guarda."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--ingest", action="store_true", help="Consultar sólo los tres RSS revisados al aplicar.")

    def handle(self, *args, **options):
        if options["ingest"] and not options["apply"]:
            raise CommandError("--ingest requiere --apply.")
        self.stdout.write(json.dumps({"mode": "apply" if options["apply"] else "preview",
                                      "sources": [row[0] for row in REVIEWED_FEEDS],
                                      "elpais_feeds": Feed.objects.filter(source__name="EL PAÍS").count()}))
        if not options["apply"]:
            return
        selected = []
        with transaction.atomic():
            removed = Feed.objects.filter(source__name="EL PAÍS").update(
                is_active=False, show_summary=False, show_images=False,
                allow_ai_briefing=False, allow_ai_grouping=False,
            )
            argentina = Category.objects.get(slug="argentina")
            for name, website, section, url in REVIEWED_FEEDS:
                source, _ = Source.objects.get_or_create(name=name, defaults={"website_url": website})
                feed, created = Feed.objects.get_or_create(url=url, defaults={
                    "source": source, "name": section, "language": "es", "is_active": True,
                    "show_summary": True, "show_images": False,
                    "allow_ai_briefing": True, "allow_ai_grouping": True,
                })
                if feed.source_id != source.pk:
                    raise CommandError("Una URL revisada pertenece a otra fuente; no se aplicaron cambios.")
                if created:
                    feed.categories.add(argentina)
                # Una ejecución posterior no reactiva feeds pausados ni revierte permisos del administrador.
                selected.append(feed)
        self.stdout.write(f"Configuración aplicada: {removed} feeds de EL PAÍS desactivados; tres medios argentinos revisados.")
        if options["ingest"]:
            errors = 0
            for feed in selected:
                if not feed.is_active:
                    self.stdout.write(f"{feed.source.name}: pausado; se conserva su estado.")
                    continue
                try:
                    result = ingest_feed(feed)
                except IngestionError as error:
                    errors += 1
                    self.stderr.write(f"{feed.source.name}: {error}")
                    continue
                self.stdout.write(json.dumps({"source": feed.source.name, "new": result.created,
                                              "duplicates": result.duplicates, "skipped": result.skipped,
                                              "descriptions": feed.articles.exclude(summary="").count()}))
            if errors:
                raise CommandError(f"Fallaron {errors} RSS revisados; se conservan las importaciones correctas.")
