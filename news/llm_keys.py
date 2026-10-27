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


def with_secondary_on_quota(task, api_key, request):
    """Una sola alternativa para clasificación/agrupamiento; nunca registra claves."""
    try:
        return request(api_key)
    except Exception as error:
        cause = error if isinstance(error, errors.APIError) else error.__cause__
        primary = os.environ.get("GEMINI_API_KEY", "").strip()
        secondary = os.environ.get("GEMINI_API_KEY_SECONDARY", "").strip()
        if (task not in {"classification", "grouping"} or not primary or api_key != primary
                or not secondary or secondary == primary
                or not isinstance(cause, errors.APIError) or cause.code != 429):
            raise
        logging.getLogger(__name__).warning(
            "Gemini %s: cuota de clave principal no disponible; se intenta la secundaria.", task,
        )
        return request(secondary)


def configured_tasks():
    return [task for task in TASK_API_KEYS if api_key_for(task)]
