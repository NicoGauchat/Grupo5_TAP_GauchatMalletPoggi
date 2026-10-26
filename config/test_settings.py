"""Configuración aislada para las pruebas automatizadas del proyecto."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "clave-exclusiva-para-pruebas-locales")

from .settings import *  # noqa: E402,F403


SECRET_KEY = "clave-exclusiva-para-pruebas-locales"
AI_REQUEST_INTERVAL_SECONDS = 0
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# El cliente de pruebas no necesita HTTPS ni collectstatic de producción.
SECURE_SSL_REDIRECT = False
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MIDDLEWARE = [
    middleware for middleware in MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
