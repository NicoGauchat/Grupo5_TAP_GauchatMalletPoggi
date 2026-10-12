"""Configuración aislada para las pruebas automatizadas del proyecto."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "clave-exclusiva-para-pruebas-locales")

from .settings import *  # noqa: E402,F403


SECRET_KEY = "clave-exclusiva-para-pruebas-locales"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
