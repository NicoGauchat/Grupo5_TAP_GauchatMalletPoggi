"""Diagnósticos por lista permitida: nunca incluyen mensajes ni respuestas del proveedor."""

import json

import httpx
from google.genai import errors


def safe_diagnostic(error):
    if isinstance(error, errors.APIError):
        code = error.code
        status = str(code) if type(code) is int and 100 <= code <= 599 else "unknown"
        reason = {
            400: "invalid_request", 401: "unauthenticated", 402: "payment_required",
            403: "permission_denied", 404: "not_found", 408: "request_timeout",
            429: "quota", 500: "provider_internal", 502: "bad_gateway",
            503: "provider_unavailable", 504: "provider_timeout",
        }.get(code, "api_error") if type(code) is int else "api_error"
        return f"Gemini HTTP={status} reason={reason}"
    if isinstance(error, (httpx.TimeoutException, TimeoutError)):
        return "Gemini reason=timeout"
    if isinstance(error, httpx.TransportError):
        return "Gemini reason=transport"
    if isinstance(error, json.JSONDecodeError):
        return "Gemini reason=invalid_json"
    return "Gemini reason=client_error"
