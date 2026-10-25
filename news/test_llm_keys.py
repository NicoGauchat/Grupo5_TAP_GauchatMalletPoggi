import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from google.genai import errors

from .briefings import briefing_context
from .llm_briefing import BriefingError, summarize_articles
from .llm_classification import ClassificationError, classify_batch
from .llm_grouping import GroupingError, group_articles
from .llm_importance import ImportanceError, score_stories
from .llm_keys import TASK_API_KEYS, api_key_for, configured_tasks
from .models import Article, Feed, Source


PRIMARY = "primary-test-value"
SECONDARY = "secondary-test-value"


class APIKeyRoutingTests(SimpleTestCase):
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
                               feed=SimpleNamespace(source=SimpleNamespace(name="Fuente de ensayo")))

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
             {"items": []}, SECONDARY),
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
        Article.objects.create(feed=feed, title="Titular sintético", original_url="https://example.com/editorial-key/news",
                               published_at=now)
        self.assertEqual(briefing_context(now)["briefing_state"], "pending")
