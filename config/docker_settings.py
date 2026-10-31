"""Perfil HTTP local de Compose: PostgreSQL sólo en la red Docker."""
from .settings import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
