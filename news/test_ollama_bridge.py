import json
import os
import threading
import time
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase

from . import ollama
from .ollama_bridge import BridgeServer
from .llm_classification import classify_batch


class BridgeTests(SimpleTestCase):
    def setUp(self):
        self.token = "test-only-token-" + "x" * 32
        self.server = BridgeServer(("127.0.0.1", 0), self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.server.server_port}", trust_env=False)
        self.headers = {"Authorization": "Bearer " + self.token}

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_unauthorized_requests_and_raw_ollama_routes_are_rejected(self):
        self.assertEqual(self.client.get("/health").status_code, 401)
        self.assertEqual(self.client.post("/jobs", json={}).status_code, 401)
        self.assertEqual(self.client.post("/api/generate", headers=self.headers).status_code, 404)

    def test_model_and_payload_are_restricted(self):
        response = self.client.post("/jobs", headers=self.headers, json={
            "endpoint": "/api/generate", "payload": {"model": "unreviewed-model", "prompt": "ficticio"}})
        self.assertEqual(response.status_code, 400)

    def test_expired_result_is_not_returned(self):
        with self.server.lock:
            self.server.jobs["old"] = {"created": time.monotonic() - 601, "status": "done", "response": {"text": "ficticio"}}
        self.assertEqual(self.client.get("/jobs/old", headers=self.headers).status_code, 404)
        with self.server.lock:
            self.assertNotIn("old", self.server.jobs)
        response = self.client.post("/jobs", headers=self.headers, json={
            "endpoint": "/api/pull", "payload": {"model": "qwen3:4b-instruct"}})
        self.assertEqual(response.status_code, 400)

    @patch("news.ollama_bridge.httpx.post")
    def test_authenticated_async_request_returns_only_its_result(self, inference):
        inference.return_value = httpx.Response(200, request=httpx.Request("POST", "http://localhost"), json={"response": '{"ok":true}'})
        response = self.client.post("/jobs", headers=self.headers, json={
            "endpoint": "/api/generate", "payload": {"model": "qwen3:4b-instruct", "prompt": "ficticio"}})
        self.assertEqual(response.status_code, 202)
        identifier = response.json()["job_id"]
        for _ in range(20):
            result = self.client.get("/jobs/" + identifier, headers=self.headers).json()
            if result["status"] == "done":
                break
            time.sleep(.01)
        self.assertEqual(result["response"]["response"], '{"ok":true}')
        self.assertEqual(self.client.get("/jobs/" + identifier).status_code, 401)
        self.assertNotIn(self.token, json.dumps(result))
        self.assertEqual(inference.call_args.args[0], "http://127.0.0.1:11434/api/generate")


class RemoteClientTests(SimpleTestCase):
    @patch.dict(os.environ, {"OLLAMA_BRIDGE_URL": "http://unsafe.example", "OLLAMA_BRIDGE_TOKEN": "x" * 40}, clear=True)
    @patch("news.ollama.httpx.get")
    def test_unsafe_url_never_receives_credentials(self, request):
        self.assertFalse(ollama.remote_available())
        request.assert_not_called()

    @patch.dict(os.environ, {"OLLAMA_BRIDGE_URL": "https://example.trycloudflare.com", "OLLAMA_BRIDGE_TOKEN": "x" * 40}, clear=True)
    @patch("news.ollama.httpx.get", side_effect=httpx.ConnectError("offline"))
    def test_offline_pc_is_not_available(self, request):
        self.assertFalse(ollama.remote_available())

    @patch.dict(os.environ, {"OLLAMA_BRIDGE_URL": "https://example.trycloudflare.com", "OLLAMA_BRIDGE_TOKEN": "x" * 40}, clear=True)
    @patch("news.ollama.httpx.post")
    @patch("news.ollama.httpx.get")
    def test_async_response_is_polled_over_short_authenticated_requests(self, get, post):
        def result(data, code=200):
            return httpx.Response(code, request=httpx.Request("GET", "https://example.trycloudflare.com"), json=data)
        get.side_effect = [result({"ready": True}), result({"status": "done", "response": {"response": "ficticio"}})]
        post.return_value = result({"job_id": "a" * 32}, 202)
        self.assertEqual(ollama.post_inference("/api/generate", {"model": "qwen3:4b-instruct"}, 5), {"response": "ficticio"})
        self.assertEqual(post.call_args.args[0], "https://example.trycloudflare.com/jobs")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer " + "x" * 40)
