"""Asignación de credenciales Gemini y respaldo secundario ante cuota principal."""

import logging
import os

from google.genai import errors

GEMINI_MODELS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")


def configured_model():
    model = os.getenv("GEMINI_MODEL", "").strip() or GEMINI_MODELS[0]
    if model not in GEMINI_MODELS:
        raise ValueError("GEMINI_MODEL debe ser un modelo gratuito habilitado en el proyecto.")
    return model


TASK_API_KEYS = {
    "classification": "GEMINI_API_KEY",
    "grouping": "GEMINI_API_KEY",
    "importance": "GEMINI_API_KEY_SECONDARY",
    "briefing": "GEMINI_API_KEY_SECONDARY",
}


def api_key_for(task):
    assigned = os.environ.get(TASK_API_KEYS[task], "").strip()
    return (assigned or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY_SECONDARY", "").strip())


def is_quota_error(error):
    """Reconoce cuota sin analizar mensajes que puedan contener datos privados."""
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if (isinstance(error, errors.APIError) and error.code == 429
                or getattr(error, "code", None) == "quota"):
            return True
        error = error.__cause__
    return False


def with_secondary_on_quota(task, api_key, request):
    """Prueba la otra clave configurada una sola vez ante cuota, en todas las tareas."""
    try:
        return request(api_key)
    except Exception as error:
        primary = os.environ.get("GEMINI_API_KEY", "").strip()
        secondary = os.environ.get("GEMINI_API_KEY_SECONDARY", "").strip()
        alternative = next((key for key in (primary, secondary) if key and key != api_key), None)
        if not alternative or not is_quota_error(error):
            raise
        logging.getLogger(__name__).warning(
            "Gemini %s: cuota no disponible; se intenta la otra clave configurada.", task,
        )
        return request(alternative)


def configured_tasks():
    return [task for task in TASK_API_KEYS if api_key_for(task)]
