"""Puente temporal autenticado: sólo inferencia, sin conexión a la base de datos."""

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import secrets
import threading
import time

from dotenv import dotenv_values
import httpx


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, token, model="qwen3:4b-instruct"):
        if len(token) < 32:
            raise ValueError("El puente requiere un token de al menos 32 caracteres.")
        self.token, self.model = token, model
        self.jobs, self.lock = {}, threading.Lock()
        self.stopping = threading.Event()
        self.worker = ThreadPoolExecutor(max_workers=1)
        super().__init__(address, BridgeHandler)
        self.cleaner = threading.Thread(target=self.expire_jobs, daemon=True)
        self.cleaner.start()

    def expire_jobs(self):
        while not self.stopping.wait(10):
            with self.lock:
                now = time.monotonic()
                self.jobs = {key: value for key, value in self.jobs.items() if now - value["created"] < 600}

    def submit(self, endpoint, payload):
        with self.lock:
            now = time.monotonic()
            self.jobs = {key: value for key, value in self.jobs.items() if now - value["created"] < 600}
            completed = sorted((key for key, value in self.jobs.items() if value["status"] != "pending"),
                               key=lambda key: self.jobs[key]["created"])
            for key in completed[:-30]:
                del self.jobs[key]
            if sum(job["status"] == "pending" for job in self.jobs.values()) >= 2:
                return None
            identifier = secrets.token_hex(16)
            self.jobs[identifier] = {"status": "pending", "created": now}
        self.worker.submit(self.infer, identifier, endpoint, payload)
        return identifier

    def infer(self, identifier, endpoint, payload):
        try:
            response = httpx.post("http://127.0.0.1:11434" + endpoint, json=payload,
                                  timeout=httpx.Timeout(300, connect=2), trust_env=False)
            response.raise_for_status()
            result = {"status": "done", "response": response.json()}
        except Exception:
            result = {"status": "failed", "code": "ollama_unavailable_or_invalid"}
        with self.lock:
            if identifier in self.jobs:
                self.jobs[identifier].update(result)

    def server_close(self):
        self.stopping.set()
        self.cleaner.join(timeout=1)
        super().server_close()
        self.worker.shutdown(wait=True, cancel_futures=True)


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # No registrar tokens, titulares ni cuerpos de peticiones.

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        given = self.headers.get("Authorization", "")
        if not hmac.compare_digest(given.encode(), ("Bearer " + self.server.token).encode()):
            self.reply(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        if self.path == "/health":
            try:
                response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2, trust_env=False)
                response.raise_for_status()
                names = {model["name"] for model in response.json()["models"]}
                ready = self.server.model in names and "embeddinggemma:300m-qat-q4_0" in names
            except Exception:
                ready = False
            self.reply(200 if ready else 503, {"ready": ready})
        elif self.path.startswith("/jobs/"):
            with self.server.lock:
                job = self.server.jobs.get(self.path.removeprefix("/jobs/"))
                if job and time.monotonic() - job["created"] >= 600:
                    del self.server.jobs[self.path.removeprefix("/jobs/")]
                    job = None
                result = {key: value for key, value in job.items() if key != "created"} if job else None
            self.reply(200 if result else 404, result or {"error": "not_found"})
        else:
            self.reply(404, {"error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/jobs":
            self.reply(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100_000:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            endpoint, payload = data["endpoint"], data["payload"]
            expected = {"/api/generate": self.server.model, "/api/embed": "embeddinggemma:300m-qat-q4_0"}
            if endpoint not in expected or not isinstance(payload, dict) or payload.get("model") != expected[endpoint]:
                raise ValueError()
            if endpoint == "/api/generate":
                if not isinstance(payload.get("prompt"), str) or len(payload["prompt"]) > 30_000:
                    raise ValueError()
                payload = {"model": self.server.model, "prompt": payload["prompt"],
                           "format": payload.get("format", "json"), "stream": False, "think": False,
                           "keep_alive": "2m", "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2048}}
            else:
                inputs = payload.get("input")
                if (not isinstance(inputs, list) or not 1 <= len(inputs) <= 32
                        or any(not isinstance(text, str) or len(text) > 1000 for text in inputs)):
                    raise ValueError()
                payload = {"model": expected[endpoint], "input": inputs, "truncate": False,
                           "keep_alive": "0" if payload.get("keep_alive") == "0" else "2m"}
        except (ValueError, KeyError, TypeError):
            self.reply(400, {"error": "invalid_request"})
            return
        identifier = self.server.submit(endpoint, payload)
        self.reply(202 if identifier else 429, {"job_id": identifier} if identifier else {"error": "busy"})


if __name__ == "__main__":
    config = dotenv_values(Path(__file__).resolve().parent.parent / ".env.ollama-tunnel")
    server = BridgeServer(("127.0.0.1", 11435), config.get("OLLAMA_BRIDGE_TOKEN", ""))
    print("Puente de inferencia listo en loopback:11435; autenticación obligatoria.", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
