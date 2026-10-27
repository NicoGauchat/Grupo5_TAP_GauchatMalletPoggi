import json
from types import SimpleNamespace
from unittest.mock import patch, call

import httpx
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from google.genai import errors

from .llm_briefing import BriefingError, summarize_articles
from .llm_grouping import GroupingError, group_articles
from .llm_transport import BackupError, GROQ_MODEL, backup_providers, groq_json, pace_request


class BackupTransportTests(SimpleTestCase):
    @patch.dict("os.environ", {"GROQ_API_KEY": "private-backup-key"}, clear=True)
    def test_bad_request_diagnostics_only_expose_allowlisted_codes_or_parameters(self):
        cases = [({"code": "json_validate_failed", "message": "private-response"}, "json_validate_failed"),
                 ({"param": "response_format", "message": "private-response"}, "configuration_response_format"),
                 ({"code": "private-response", "param": "private-response"}, "configuration")]
        for details, expected in cases:
            with self.subTest(expected=expected), patch("news.llm_transport.httpx.Client") as client:
                post = client.return_value.__enter__.return_value.post
                post.return_value.status_code = 400
                post.return_value.json.return_value = {"error": details}
                with self.assertRaises(BackupError) as caught:
                    groq_json("synthetic", {}, "grouping")
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn("private-response", str(caught.exception))

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "unused-test-key"}, clear=True)
    def test_excluded_provider_does_not_enable_backup(self):
        self.assertEqual(backup_providers(), [])

    @patch.dict("os.environ", {"GROQ_API_KEY": "private-backup-key"}, clear=True)
    def test_transport_uses_fixed_endpoint_and_structured_output_without_logging_secrets(self):
        with patch("news.llm_transport.httpx.Client") as client, self.assertLogs("news.llm_transport", level="WARNING") as logs:
            post = client.return_value.__enter__.return_value.post
            post.return_value.status_code = 200
            post.return_value.json.return_value = {"choices": [{"message": {"content": '{"items": []}'}}]}
            result = groq_json("synthetic headline", {"type": "OBJECT", "properties": {"items": {"type": "ARRAY", "items": {"type": "STRING"}}}, "required": ["items"]}, "briefing")
            self.assertEqual(result, {"items": []})
            self.assertEqual(post.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
            body = post.call_args.kwargs["json"]
            self.assertEqual(body["model"], GROQ_MODEL)
            self.assertEqual(body["reasoning_effort"], "low")
            self.assertEqual(body["max_completion_tokens"], 4096)
            schema = body["response_format"]["json_schema"]["schema"]
            self.assertEqual(schema["type"], "object")
            self.assertFalse(schema["additionalProperties"])
            self.assertNotIn("private-backup-key", json.dumps(body))
            self.assertNotIn("private-backup-key", " ".join(logs.output))
            self.assertNotIn("synthetic headline", " ".join(logs.output))

    @patch.dict("os.environ", {"GROQ_API_KEY": "private-backup-key"}, clear=True)
    def test_backup_errors_never_expose_raw_messages_or_retry_another_key(self):
        for status, expected in ((400, "configuration"), (401, "configuration"), (413, "request_too_large"), (429, "quota"), (503, "connection")):
            with self.subTest(status=status), patch("news.llm_transport.httpx.Client") as client:
                post = client.return_value.__enter__.return_value.post
                post.return_value.status_code = status
                post.return_value.text = "private-backup-key sensitive-response"
                with self.assertRaises(BackupError) as caught:
                    groq_json("synthetic", {}, "grouping")
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn("private-backup-key", str(caught.exception))
                self.assertNotIn("sensitive-response", str(caught.exception))
                self.assertEqual(post.call_count, 1)

    @override_settings(AI_REQUEST_INTERVAL_SECONDS=8)
    def test_requests_are_spaced_without_storing_raw_keys(self):
        with patch.dict("news.llm_transport._last_request", {}, clear=True) as state, patch("news.llm_transport.time.monotonic", side_effect=[100, 108, 110, 116]), patch("news.llm_transport.time.sleep") as sleep:
            pace_request("gemini", "private-key")
            pace_request("gemini", "private-key")
            self.assertEqual(sleep.call_args_list, [call(8), call(6)])
            self.assertNotIn("private-key", str(state))


@patch.dict("os.environ", {"GEMINI_API_KEY": "primary-test", "GROQ_API_KEY": "backup-test"}, clear=True)
class CriticalFallbackTests(SimpleTestCase):
    def articles(self):
        return [SimpleNamespace(pk=pk, title="Titular sintético", language="es", published_at=timezone.now(),
            feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")),
            categories=SimpleNamespace(all=lambda: [SimpleNamespace(slug="ciencia", name="Ciencia")]),
            llm_categories=SimpleNamespace(all=lambda: [])) for pk in (1, 2)]

    def test_briefing_uses_backup_after_unavailability_or_invalid_references(self):
        valid = {"items": [{"category_slug": "ciencia", "text": "Síntesis ficticia.", "importance_score": 3, "article_ids": [1]}]}
        for failure in (errors.APIError(503, {}), None):
            with self.subTest(failure=failure), patch("news.llm_briefing.genai.Client") as client, patch("news.llm_briefing.request_backup", return_value=valid) as backup:
                generate = client.return_value.models.generate_content
                generate.side_effect = failure
                generate.return_value.text = json.dumps({"items": [dict(valid["items"][0], article_ids=[999])]})
                result = summarize_articles(self.articles())
                self.assertEqual(result, valid["items"])
                self.assertEqual(result.model, f"groq:{GROQ_MODEL}")
                backup.assert_called_once()

    def test_invalid_backup_is_rejected_and_configuration_does_not_fallback(self):
        with patch("news.llm_briefing.genai.Client") as client, patch("news.llm_briefing.request_backup", return_value={"items": []}) as backup:
            client.return_value.models.generate_content.side_effect = errors.APIError(503, {})
            with self.assertRaises(BriefingError):
                summarize_articles(self.articles())
            backup.assert_called_once()
            backup.reset_mock()
            client.return_value.models.generate_content.side_effect = errors.APIError(403, {})
            with self.assertRaises(BriefingError):
                summarize_articles(self.articles())
            backup.assert_not_called()

    def test_grouping_backup_reruns_proposal_and_audit_and_returns_provider(self):
        def request(prompt, schema, key, *, provider="gemini"):
            if provider == "gemini":
                raise GroupingError("Gemini reason=quota", retryable=False, fallback_allowed=True)
            if "groups" in schema["properties"]:
                return {"groups": [{"story_id": 0, "article_ids": [1, 2]}]}
            return {"decisions": [{"article_id": 2, "same_event": True, "reason": "Mismo hecho sintético."}]}
        with patch("news.llm_grouping.request_groups", side_effect=request) as model:
            result = group_articles(self.articles(), [])
            self.assertEqual(result, [{"story_id": 0, "article_ids": [1, 2]}])
            self.assertEqual(result.model, f"groq:{GROQ_MODEL}")
            self.assertEqual(model.call_count, 3)
            self.assertEqual([c.kwargs.get("provider", "gemini") for c in model.call_args_list], ["gemini", "groq", "groq"])

    def test_grouping_never_accepts_bad_backup_references(self):
        with patch("news.llm_grouping.request_groups", side_effect=[
            GroupingError("Gemini unavailable", retryable=False, fallback_allowed=True),
            {"groups": [{"story_id": 0, "article_ids": [999]}]},
        ]) as model:
            with self.assertRaisesRegex(GroupingError, "reason=unknown_article_id"):
                group_articles(self.articles(), [])
            self.assertEqual(model.call_count, 2)
