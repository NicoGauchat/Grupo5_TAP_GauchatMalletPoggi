"""Aplica la decisión explícita de habilitar síntesis y bajadas en todos los feeds."""

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from news.models import Feed


class Command(BaseCommand):
    help = "Simula habilitar síntesis y bajadas en todos los feeds activos; --apply aplica e incluye EL PAÍS."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        with transaction.atomic():
            elpais = Feed.objects.filter(source__name="EL PAÍS")
            candidates = Feed.objects.filter(is_active=True) | elpais
            result = {"mode": "apply" if options["apply"] else "preview", "feeds": candidates.count(),
                      "elpais_reactivated": elpais.filter(is_active=False).count(),
                      "briefing_enabled": candidates.filter(allow_ai_briefing=False).count(),
                      "descriptions_enabled": candidates.filter(show_summary=False).count()}
            if options["apply"]:
                elpais.update(is_active=True, allow_ai_grouping=True)
                Feed.objects.filter(is_active=True).update(allow_ai_briefing=True, show_summary=True)
        self.stdout.write(json.dumps(result))
