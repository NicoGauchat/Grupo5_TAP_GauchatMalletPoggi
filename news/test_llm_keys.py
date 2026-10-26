import json
import httpx
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from google.genai import errors
from google import genai

from .briefings import briefing_context
from .llm_briefing import BriefingError, summarize_articles
from .llm_classification import ClassificationError, classify_batch
from .llm_grouping import GroupingError, group_articles
from .llm_importance import ImportanceError, score_stories
from .llm_keys import TASK_API_KEYS, api_key_for, configured_tasks
from .llm_diagnostics import safe_diagnostic
from .models import Article, Category, Feed, Source


PRIMARY = "primary-test-value"
SECONDARY = "secondary-test-value"


class APIKeyRoutingTests(SimpleTestCase):
    @patch.dict("os.environ", {"GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_sdk_retries_unavailable_but_not_quota_with_mock_http(self):
        real_client = genai.Client
        result = {"items": [{"category_slug": "ciencia", "text": "Síntesis de prueba.",
                             "importance_score": 3, "article_ids": [7]}]}
        for status in (503, 429):
            calls = []

            def respond(request):
                calls.append(request)
                if len(calls) == 1:
                    return httpx.Response(status, json={"error": {"code": status, "message": "private response"}})
                return httpx.Response(200, json={"candidates": [{"content": {
                    "role": "model", "parts": [{"text": json.dumps(result)}]}, "finishReason": "STOP"}]})

            def build_client(**kwargs):
                kwargs["http_options"].client_args = {"transport": httpx.MockTransport(respond)}
                kwargs["http_options"].retry_options.initial_delay = 0.001
                kwargs["http_options"].retry_options.max_delay = 0.001
                return real_client(**kwargs)

            with self.subTest(status=status), patch("news.llm_briefing.genai.Client", side_effect=build_client):
                if status == 503:
                    self.assertEqual(summarize_articles([self.article()]), result["items"])
                    self.assertEqual(len(calls), 2)
                else:
                    with self.assertRaises(BriefingError) as caught:
                        summarize_articles([self.article()])
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(caught.exception.code, "quota")
                    self.assertNotIn("private response", str(caught.exception))

    @patch.dict("os.environ", {"GEMINI_API_KEY": PRIMARY, "GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_provider_failures_report_safe_http_diagnostics_in_all_tasks(self):
        article = self.article()
        cases = [
            ("news.llm_classification.genai.Client", lambda: classify_batch([article], ["ciencia"]), ClassificationError),
            ("news.llm_grouping.genai.Client", lambda: group_articles([article], []), GroupingError),
            ("news.llm_importance.genai.Client", lambda: score_stories({9: [article]}), ImportanceError),
            ("news.llm_briefing.genai.Client", lambda: summarize_articles([article]), BriefingError),
        ]
        for code in (400, 401, 403, 404, 429, 500, 503, 504):
            for path, operation, exception in cases:
                with self.subTest(code=code, path=path), patch(path) as client:
                    error = errors.APIError(code, {"error": {"message": SECONDARY + " private headline"}})
                    client.return_value.models.generate_content.side_effect = error
                    client.return_value.__enter__.return_value.models.generate_content.side_effect = error
                    with self.assertRaises(exception) as caught:
                        operation()
                    self.assertIn(f"Gemini HTTP={code}", str(caught.exception))
                    self.assertNotIn(SECONDARY, str(caught.exception))
                    self.assertNotIn("private headline", str(caught.exception))

    def test_non_api_diagnostics_do_not_echo_exception_content(self):
        cases = [
            (TimeoutError(SECONDARY), "timeout"),
            (httpx.ConnectError(SECONDARY), "transport"),
            (json.JSONDecodeError(SECONDARY, "private headline", 0), "invalid_json"),
            (ValueError(SECONDARY), "client_error"),
        ]
        for error, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(safe_diagnostic(error), f"Gemini reason={reason}")

    @patch.dict("os.environ", {"GEMINI_API_KEY": PRIMARY, "GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_two_credentials_have_fixed_task_assignments(self):
        self.assertEqual([api_key_for(task) for task in TASK_API_KEYS], [PRIMARY, PRIMARY, SECONDARY, SECONDARY])
        self.assertEqual(configured_tasks(), list(TASK_API_KEYS))

    def test_existing_single_key_configuration_keeps_working(self):
        for secondary in (None, "", "   "):
            values = {"GEMINI_API_KEY": "  " + PRIMARY + "  "}
            if secondary is not None:
                values["GEMINI_API_KEY_SECONDARY"] = secondary
            with self.subTest(secondary=secondary), patch.dict("os.environ", values, clear=True):
                self.assertEqual([api_key_for(task) for task in TASK_API_KEYS], [PRIMARY] * 4)

    @patch.dict("os.environ", {"GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_only_secondary_enables_editorial_tasks(self):
        self.assertEqual(configured_tasks(), ["importance", "briefing"])
        self.assertEqual(api_key_for("classification"), "")
        self.assertEqual(api_key_for("grouping"), "")

    @patch.dict("os.environ", {}, clear=True)
    def test_no_credentials_disables_all_tasks(self):
        self.assertEqual(configured_tasks(), [])

    def article(self):
        return SimpleNamespace(pk=7, title="Titular sintético", language="es", published_at=timezone.now(),
                               feed=SimpleNamespace(source=SimpleNamespace(name="Fuente de ensayo")),
                               categories=SimpleNamespace(all=lambda: [SimpleNamespace(slug="ciencia", name="Ciencia")]),
                               llm_categories=SimpleNamespace(all=lambda: []))

    @patch.dict("os.environ", {"GEMINI_API_KEY": PRIMARY, "GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_all_clients_receive_the_assigned_key(self):
        article = self.article()
        cases = [
            ("classification", "news.llm_classification.genai.Client", lambda: classify_batch([article], ["ciencia"]),
             {"articles": [{"article_id": 7, "categories": ["ciencia"]}]}, PRIMARY),
            ("grouping", "news.llm_grouping.genai.Client", lambda: group_articles([article], []),
             {"groups": [{"story_id": 0, "article_ids": [7]}]}, PRIMARY),
            ("importance", "news.llm_importance.genai.Client", lambda: score_stories({9: [article]}),
             {"stories": [{"story_id": 9, "score": 3, "reason": "Alcance limitado."}]}, SECONDARY),
            ("briefing", "news.llm_briefing.genai.Client", lambda: summarize_articles([article]),
             {"items": [{"category_slug": "ciencia", "text": "Síntesis de prueba.", "importance_score": 3, "article_ids": [7]}]}, SECONDARY),
        ]
        for task, path, operation, response, expected in cases:
            with self.subTest(task=task), patch(path) as client:
                text = json.dumps(response)
                client.return_value.models.generate_content.return_value.text = text
                client.return_value.__enter__.return_value.models.generate_content.return_value.text = text
                operation()
                self.assertEqual(client.call_args.kwargs["api_key"], expected)
                self.assertEqual(client.call_count, 1)

    @patch.dict("os.environ", {"GEMINI_API_KEY": PRIMARY, "GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_quota_does_not_switch_to_the_other_key(self):
        article = self.article()
        cases = [
            ("news.llm_briefing.genai.Client", lambda: summarize_articles([article]), BriefingError),
            ("news.llm_importance.genai.Client", lambda: score_stories({9: [article]}), ImportanceError),
        ]
        for path, operation, exception in cases:
            with self.subTest(path=path), patch(path) as client:
                error = errors.ClientError(429, {"error": {"message": "provider-private-message"}})
                client.return_value.models.generate_content.side_effect = error
                client.return_value.__enter__.return_value.models.generate_content.side_effect = error
                with self.assertRaises(exception) as caught:
                    operation()
                self.assertEqual(client.call_count, 1)
                self.assertEqual(client.call_args.kwargs["api_key"], SECONDARY)
                self.assertNotIn("provider-private-message", str(caught.exception))

    @patch.dict("os.environ", {"GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_secondary_does_not_run_unassigned_primary_tasks(self):
        with patch("news.llm_classification.genai.Client") as client:
            with self.assertRaises(ClassificationError):
                classify_batch([self.article()], ["ciencia"])
            with self.assertRaises(GroupingError):
                group_articles([self.article()], [])
            client.assert_not_called()


class EditorialKeyStateTests(TestCase):
    @patch.dict("os.environ", {"GEMINI_API_KEY_SECONDARY": SECONDARY}, clear=True)
    def test_briefing_accepts_secondary_only_configuration(self):
        Feed.objects.update(is_active=False)
        feed = Feed.objects.create(source=Source.objects.create(name="Fuente de clave editorial"), name="RSS",
                                   url="https://example.com/editorial-key/rss", is_active=True, allow_ai_briefing=True)
        now = timezone.now()
        article = Article.objects.create(feed=feed, title="Titular sintético", original_url="https://example.com/editorial-key/news",
                                         published_at=now)
        category = Category.objects.get(slug="ciencia")
        article.categories.add(category)
        self.assertEqual(briefing_context(now, [category])["category_briefings"][0]["state"], "pending")
