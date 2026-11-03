"""Espaciado local y respaldos gratuitos explícitos con endpoints fijos."""

import hashlib
import json
import logging
import os
import re
import time

import httpx
from django.conf import settings


GROQ_MODEL = "openai/gpt-oss-120b"
CLOUDFLARE_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
BACKUPS = {
    "groq": ("GROQ_API_KEY", GROQ_MODEL, "https://api.groq.com/openai/v1/chat/completions"),
    "cloudflare": ("CLOUDFLARE_API_TOKEN", CLOUDFLARE_MODEL,
                   "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/" + CLOUDFLARE_MODEL),
}
_last_request = {}


class BackupError(Exception):
    def __init__(self, code, provider="groq", http_status=None):
        status = f" HTTP={http_status}" if type(http_status) is int and 100 <= http_status <= 599 else ""
        super().__init__(f"Respaldo {provider} no produjo una respuesta válida.{status} reason={code}")
        self.code = code


class ModelList(list):
    def __init__(self, values, model):
        super().__init__(values)
        self.model = model


def decode_json(content):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise json.JSONDecodeError("duplicate_key", "", 0)
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique_object)


def backup_configured():
    return bool(backup_providers())


def backup_providers():
    return [provider for provider, (key, _, _) in BACKUPS.items() if os.getenv(key, "").strip()
            and (provider != "cloudflare" or os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip())]


def backup_model(provider):
    return f"{provider}:{BACKUPS[provider][1]}"


def pace_request(provider, api_key):
    interval = settings.AI_REQUEST_INTERVAL_SECONDS
    if interval <= 0:
        return
    identity = (provider, hashlib.sha256(api_key.encode()).digest())
    now = time.monotonic()
    previous = _last_request.get(identity, now)
    delay = max(0, previous + interval - now)
    if delay:
        time.sleep(delay)
    _last_request[identity] = time.monotonic()


def _strict_schema(value):
    if isinstance(value, list):
        return [_strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _strict_schema(item) for key, item in value.items()}
    if isinstance(result.get("type"), str):
        result["type"] = result["type"].lower()
    if result.get("type") == "object":
        result["additionalProperties"] = False
    return result


def groq_json(prompt, schema, task):
    return request_backup(prompt, schema, task, "groq")


def request_backup_chain(prompt, schema, task):
    """Agota respaldos configurados ante cuota o indisponibilidad, sin repetir proveedores."""
    last_error = BackupError("missing_key")
    for provider in backup_providers():
        try:
            return request_backup(prompt, schema, task, provider), backup_model(provider)
        except BackupError as error:
            if error.code not in {"quota", "timeout", "connection"}:
                raise
            logging.getLogger(__name__).warning("IA %s: respaldo %s no disponible; %s", task, provider, error)
            last_error = error
    raise last_error


def request_backup(prompt, schema, task, provider):
    key_name, model, endpoint = BACKUPS[provider]
    api_key = os.getenv(key_name, "").strip()
    if not api_key:
        raise BackupError("missing_key", provider)
    if provider == "cloudflare":
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not re.fullmatch(r"[0-9a-fA-F]{32}", account_id):
            raise BackupError("configuration_account_id", provider)
        endpoint = endpoint.format(account_id=account_id)
    pace_request(provider, api_key)
    logging.getLogger(__name__).warning("IA: provider=%s model=%s task=%s", provider, model, task)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "news_response", "strict": True, "schema": _strict_schema(schema),
        }},
    }
    body.update(reasoning_effort="low", max_completion_tokens=4096)
    if provider == "cloudflare":
        body = {"messages": body["messages"], "max_tokens": 4096, "temperature": 0,
                "response_format": {"type": "json_schema", "json_schema": _strict_schema(schema)}}
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json=body,
            )
            if response.status_code != 200:
                code = "request_too_large" if response.status_code == 413 else "quota" if response.status_code == 429 else (
                    "configuration" if response.status_code in {400, 401, 402, 403, 404} else "connection"
                )
                if response.status_code == 400:
                    try:
                        details = response.json()
                    except ValueError:
                        details = {}
                    error = details.get("error") if isinstance(details, dict) else None
                    if isinstance(error, dict):
                        known_codes = {"json_validate_failed", "model_generation_failed", "structured_generation_failed"}
                        if isinstance(error.get("code"), str) and error["code"] in known_codes:
                            code = error["code"]
                        elif error.get("param") in ("response_format", "reasoning_effort", "max_completion_tokens"):
                            code = f"configuration_{error['param']}"
                raise BackupError(code, provider, response.status_code)
            if provider == "cloudflare":
                payload = response.json()
                if payload.get("success") is not True:
                    raise BackupError("invalid_response", provider)
                raw = payload["result"]["response"]
                result = decode_json(raw) if isinstance(raw, str) else raw
            else:
                result = decode_json(response.json()["choices"][0]["message"]["content"])
    except BackupError:
        raise
    except (httpx.TimeoutException, TimeoutError) as error:
        raise BackupError("timeout", provider) from error
    except httpx.TransportError as error:
        raise BackupError("connection", provider) from error
    except Exception as error:
        raise BackupError("invalid_response", provider) from error
    if not isinstance(result, dict):
        raise BackupError("invalid_response", provider)
    return result
