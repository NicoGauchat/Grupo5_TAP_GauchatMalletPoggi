import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local", override=True)

if os.environ.get("POSTGRES_HOST") not in {"127.0.0.1", "localhost", "::1"}:
    raise RuntimeError("El perfil local requiere PostgreSQL en esta computadora.")

from .settings import *  # noqa: E402,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
