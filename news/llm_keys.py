"""Asignación fija de las dos credenciales Gemini por función."""

import os


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
