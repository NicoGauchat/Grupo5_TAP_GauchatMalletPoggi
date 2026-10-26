"""Asignación fija de las dos credenciales Gemini por función."""

import os


GEMINI_MODELS = ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")


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
    return assigned or os.environ.get("GEMINI_API_KEY", "").strip()


def configured_tasks():
    return [task for task in TASK_API_KEYS if api_key_for(task)]
