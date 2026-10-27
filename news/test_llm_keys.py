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
from .llm_keys import TASK_API_KEYS, api_key_for, configured_tasks, configured_model
from .llm_diagnostics import safe_diagnostic
from .models import Article, Category, Feed, Source


PRIMARY = "primary-test-value"
SECONDARY = "secondary-test-value"


class APIKeyRoutingTests(SimpleTestCase):
    def test_model_selection_is_explicit_and_restricted(self):
        for value, expected in (("", "gemini-3.5-flash-lite"), ("gemini-3.1-flash-lite", "gemini-3.1-flash-lite"), ("  gemini-3.5-flash-lite  ", "gemini-3.5-flash-lite")):
            with self.subTest(value=value), patch.dict("os.environ", {"GEMINI_MODEL": value}):
                self.assertEqual(configured_model(), expected)
        with patch.dict("os.environ", {"GEMINI_MODEL": "not-an-approved-model"}):
            with self.assertRaises(ValueError):
                configured_model()

    @patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEY_SECONDARY": SECONDARY, "GROQ_API_KEY": ""})
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
                with self.subTest(code=code, path=path), patch(path) as client, patch("news.llm_grouping.time.sleep"):
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
    def test_only_secondary_enables_all_tasks(self):
        self.assertEqual(configured_tasks(), list(TASK_API_KEYS))
        self.assertEqual(api_key_for("classification"), SECONDARY)
        self.assertEqual(api_key_for("grouping"), SECONDARY)

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
             {"groups": {"7": "new:7"}}, PRIMARY),
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
    def test_secondary_alone_runs_classification_and_grouping(self):
        with patch("news.llm_classification.genai.Client") as client:
            client.return_value.models.generate_content.return_value.text = json.dumps(
                {"articles": [{"article_id": 7, "categories": ["ciencia"]}]})
            client.return_value.__enter__.return_value.models.generate_content.return_value.text = json.dumps(
                {"groups": {"7": "new:7"}})
            self.assertEqual(classify_batch([self.article()], ["ciencia"]), {7: ["ciencia"]})
            self.assertEqual(group_articles([self.article()], []), [{"story_id": 0, "article_ids": [7]}])
            self.assertEqual([call.kwargs["api_key"] for call in client.call_args_list], [SECONDARY, SECONDARY])


@patch.dict("os.environ", {"GEMINI_API_KEY": PRIMARY, "GEMINI_API_KEY_SECONDARY": SECONDARY,
                          "AI_API_FIRST": "true"}, clear=True)
class SecondaryQuotaFallbackTests(SimpleTestCase):
    def setUp(self):
        from . import ollama
        ollama._fallback_used.clear()

    def article(self, pk=7):
        article = APIKeyRoutingTests.article(self)
        article.pk = pk
        article.story_id = None
        return article

    def sdk(self, key, response):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.__enter__.return_value = client
        if key == PRIMARY:
            client.models.generate_content.side_effect = errors.APIError(429, {"error": {"message": "private"}})
        else:
            client.models.generate_content.return_value.text = json.dumps(response)
        return client

    @patch("news.ollama.request_json")
    @patch("news.llm_classification.genai.Client")
    def test_classification_secondary_quota_fallback_before_ollama(self, cloud, local):
        response = {"articles": [{"article_id": 7, "categories": ["ciencia"]}]}
        cloud.side_effect = lambda **kwargs: self.sdk(kwargs["api_key"], response)
        with self.assertLogs("news.llm_keys", "WARNING") as logs:
            result = classify_batch([self.article()], ["ciencia"])
        self.assertEqual(result, {7: ["ciencia"]})
        self.assertEqual([call.kwargs["api_key"] for call in cloud.call_args_list], [PRIMARY, SECONDARY])
        local.assert_not_called()
        self.assertNotIn(PRIMARY, str(logs.output))
        self.assertNotIn(SECONDARY, str(logs.output))

    @patch("news.ollama.request_json")
    @patch("news.llm_classification.genai.Client")
    def test_both_keys_quota_then_ollama(self, cloud, local):
        cloud.side_effect = lambda **kwargs: self.sdk(PRIMARY, {})
        local.return_value = {"articles": [{"article_id": 7, "categories": ["ciencia"]}]}
        self.assertEqual(classify_batch([self.article()], ["ciencia"]), {7: ["ciencia"]})
        self.assertEqual([call.kwargs["api_key"] for call in cloud.call_args_list], [PRIMARY, SECONDARY])
        local.assert_called_once()

    @patch.dict("os.environ", {"AI_API_FIRST": "false"})
    @patch("news.llm_classification.genai.Client")
    def test_invalid_secondary_response_is_not_saved(self, cloud):
        cloud.side_effect = lambda **kwargs: self.sdk(kwargs["api_key"], {"articles": [{"article_id": 999, "categories": []}]})
        with self.assertRaises(ClassificationError):
            classify_batch([self.article()], ["ciencia"])
        self.assertEqual(cloud.call_count, 2)

    @patch.dict("os.environ", {"AI_API_FIRST": "false"})
    @patch("news.llm_classification.genai.Client")
    def test_permission_error_does_not_consume_secondary(self, cloud):
        cloud.side_effect = errors.APIError(403, {"error": {"message": "private"}})
        with self.assertRaises(ClassificationError):
            classify_batch([self.article()], ["ciencia"])
        cloud.assert_called_once()

    @patch("news.ollama.request_json")
    @patch("news.llm_grouping.genai.Client")
    def test_grouping_secondary_also_runs_independent_identity_check(self, cloud, local):
        def sdk(**kwargs):
            response = ({"groups": {"7": "new:7", "8": "new:7"}} if cloud.call_count <= 2 else
                        {"decisions": {"8": {"same_event": False, "reason": "Hechos distintos."}}})
            return self.sdk(kwargs["api_key"], response)
        cloud.side_effect = sdk
        result = group_articles([self.article(7), self.article(8)], [])
        self.assertEqual([row["article_ids"] for row in result], [[7], [8]])
        self.assertEqual([call.kwargs["api_key"] for call in cloud.call_args_list],
                         [PRIMARY, SECONDARY, PRIMARY, SECONDARY])
        local.assert_not_called()

    @patch.dict("os.environ", {"GEMINI_API_KEY_SECONDARY": PRIMARY, "AI_API_FIRST": "false"})
    @patch("news.llm_classification.genai.Client")
    def test_identical_keys_are_not_attempted_twice(self, cloud):
        cloud.side_effect = lambda **kwargs: self.sdk(PRIMARY, {})
        with self.assertRaises(ClassificationError):
            classify_batch([self.article()], ["ciencia"])
        cloud.assert_called_once()


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
