"""Cuenta pendientes por fecha de publicación sin modificar noticias ni llamar a IA."""

import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from news.models import GROUPING_VERSION, Article
from news.retention import RETENTION_DAYS


class Command(BaseCommand):
    help = "Informa la antigüedad de las noticias pendientes de agrupamiento (sólo lectura)."

    def handle(self, *args, **options):
        now = timezone.now()
        day = now - timedelta(hours=24)
        two_days = now - timedelta(hours=48)
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
            pending = Article.objects.filter(
                feed__is_active=True,
                feed__allow_ai_grouping=True,
                published_at__gte=now - timedelta(days=RETENTION_DAYS),
                published_at__lte=now,
            ).filter(Q(story__isnull=True) | ~Q(story__grouping_version=GROUPING_VERSION))
            counts = pending.aggregate(
                total=Count("pk"),
                up_to_24h=Count("pk", filter=Q(published_at__gte=day)),
                over_24h_up_to_48h=Count("pk", filter=Q(published_at__lt=day, published_at__gte=two_days)),
                over_48h=Count("pk", filter=Q(published_at__lt=two_days)),
                legacy_groups=Count("pk", filter=Q(story__isnull=False)),
                oldest=Min("published_at"),
                newest=Max("published_at"),
            )
        self.stdout.write(json.dumps({"measured_at": now, "retention_days": RETENTION_DAYS, **counts}, default=str))
