"""Ventana temporal compartida por la ingesta, el feed y la limpieza."""

from datetime import timedelta

from django.utils import timezone


RETENTION_DAYS = 14


def retention_cutoff():
    return timezone.now() - timedelta(days=RETENTION_DAYS)
