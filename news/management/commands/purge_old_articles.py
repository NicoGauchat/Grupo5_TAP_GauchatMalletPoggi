"""Elimina artículos fuera de la ventana de conservación."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from news.models import Article
from news.retention import retention_cutoff


class Command(BaseCommand):
    help = "Elimina noticias de más de 14 días; --dry-run sólo las cuenta."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Mostrar cuántas se borrarían")

    def handle(self, *args, **options):
        cutoff = retention_cutoff()
        old_articles = Article.objects.filter(
            Q(published_at__lt=cutoff)
            | Q(published_at__isnull=True, fetched_at__lt=cutoff)
        )
        count = old_articles.count()
        if options["dry_run"]:
            self.stdout.write(f"Se eliminarían {count} noticias.")
            return
        old_articles.delete()
        self.stdout.write(f"Se eliminaron {count} noticias.")
