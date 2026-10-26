import json
from importlib import import_module
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone
from google.genai import errors

from .briefings import briefing_context
from .llm_briefing import BriefingError, summarize_articles
from .models import Article, Feed, NewsBriefing, NewsBriefingItem, Source


class BriefingResponseTests(SimpleTestCase):
    def setUp(self):
        self.article = SimpleNamespace(pk=7, title="Titular de prueba", published_at=timezone.now(),
            language="es", feed=SimpleNamespace(source=SimpleNamespace(name="Medio")))

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_validates_references_scores_and_duplicate_coverage(self, client):
        row = {"text": "Síntesis de prueba", "importance_score": 4, "article_ids": [7]}
        for rows, valid in (([row], True), ([], True), ([dict(row, importance_score=3)], True),
                            ([dict(row, article_ids=[8])], False), ([row, row], False),
                            ([dict(row, article_ids=[7, 7])], False), ([dict(row, importance_score=True)], False)):
            client.return_value.models.generate_content.return_value.text = json.dumps({"items": rows})
            with self.subTest(rows=rows):
                if valid:
                    result = summarize_articles([self.article])
                    self.assertEqual(len(result), 1 if rows and rows[0]["importance_score"] == 4 else 0)
                else:
                    with self.assertRaises(BriefingError):
                        summarize_articles([self.article])
        options = client.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, 60_000)
        self.assertEqual(options.retry_options.attempts, 1)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_failure_codes_do_not_expose_provider_messages(self, client):
        for exception, code in ((errors.ClientError(429, {"error": {"message": "secret-response"}}), "quota"),
                                (errors.ClientError(403, {}), "configuration"),
                                (errors.ServerError(503, {}), "connection"),
                                (httpx.ReadTimeout("secret-response"), "timeout"),
                                (httpx.ConnectError("secret-response"), "connection"),
                                (ValueError("secret-response"), "invalid_response")):
            client.return_value.models.generate_content.side_effect = exception
            with self.subTest(code=code), self.assertRaises(BriefingError) as caught:
                summarize_articles([self.article])
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn("secret-response", str(caught.exception))

    @patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEY_SECONDARY": ""})
    def test_missing_key_and_no_input_do_not_call_provider(self):
        with patch("news.llm_briefing.genai.Client") as client:
            self.assertEqual(summarize_articles([]), [])
            with self.assertRaises(BriefingError) as caught:
                summarize_articles([self.article])
            self.assertEqual(caught.exception.code, "missing_key")
            client.assert_not_called()


@patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
class BriefingTests(TestCase):
    def setUp(self):
        Feed.objects.update(is_active=False)
        self.feed = Feed.objects.create(source=Source.objects.create(name="Medio del resumen"),
            name="RSS", url="https://example.com/briefing", is_active=True, allow_ai_briefing=True)
        self.now = timezone.now()
        self.article = Article.objects.create(feed=self.feed, title="Hecho relevante",
            original_url="https://example.com/news", published_at=self.now - timedelta(minutes=5))
        self.user = get_user_model().objects.create_user("lector-resumen", password="prueba-local-segura")
        self.client.force_login(self.user)

    def generate(self, rows=None, **options):
        rows = rows if rows is not None else [{"text": "Síntesis de prueba", "article_ids": [self.article.pk]}]
        with patch("news.management.commands.generate_news_briefing.summarize_articles", return_value=rows) as summarize:
            call_command("generate_news_briefing", stdout=StringIO(), **options)
        return summarize

    def test_cache_force_and_expired_cache(self):
        self.generate().assert_called_once()
        self.generate().assert_not_called()
        self.generate(force=True).assert_called_once()
        self.assertEqual(NewsBriefing.objects.count(), 2)
        NewsBriefing.objects.update(generated_at=self.now - timedelta(hours=3))
        self.generate().assert_called_once()
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, "Síntesis de prueba")
        self.assertContains(response, 'href="https://example.com/news" target="_blank" rel="noopener"')
        self.assertEqual(NewsBriefing.objects.first().status, "ready")

    def test_empty_success_is_cached(self):
        self.generate(rows=[])
        self.generate().assert_not_called()
        self.assertEqual(NewsBriefing.objects.first().status, "empty")
        self.assertContains(self.client.get(reverse("news_feed")), "No surgieron sucesos")

    def test_failure_preserves_previous_valid_result_and_logs_safe_code(self):
        self.generate()
        with patch("news.management.commands.generate_news_briefing.summarize_articles",
                   side_effect=BriefingError("La cuota no está disponible.", "quota")):
            call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual((NewsBriefing.objects.first().status, NewsBriefing.objects.first().error_code), ("error", "quota"))
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, "No se pudo actualizar")
        self.assertContains(response, "Síntesis de prueba")

    def test_only_latest_250_eligible_articles_are_sent_in_stable_order(self):
        Article.objects.bulk_create([Article(feed=self.feed, title=f"Titular {i}",
            original_url=f"https://example.com/batch/{i}", published_at=self.article.published_at) for i in range(255)])
        for label, date in (("old", self.now - timedelta(hours=25)), ("future", self.now + timedelta(hours=1))):
            Article.objects.create(feed=self.feed, title=label, original_url=f"https://example.com/{label}", published_at=date)
        expected = list(Article.objects.filter(published_at=self.article.published_at).order_by("-id").values_list("pk", flat=True)[:250])
        summarize = self.generate(rows=[])
        self.assertEqual([article.pk for article in summarize.call_args.args[0]], expected)
        self.assertEqual(NewsBriefing.objects.first().article_count, 250)

    def test_no_sources_no_articles_and_missing_key_have_distinct_states(self):
        self.assertEqual(briefing_context(self.now)["briefing_state"], "pending")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEY_SECONDARY": ""}):
            call_command("generate_news_briefing", stdout=StringIO())
            self.assertEqual(NewsBriefing.objects.first().error_code, "missing_key")
            self.assertContains(self.client.get(reverse("news_feed")), "todavía no está configurado")
        Article.objects.all().delete()
        call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual(NewsBriefing.objects.first().error_code, "no_articles")
        self.assertEqual(briefing_context(timezone.now())["briefing_state"], "no_articles")
        self.feed.allow_ai_briefing = False
        self.feed.save()
        call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual(NewsBriefing.objects.first().error_code, "no_feeds")
        self.assertEqual(briefing_context(timezone.now())["briefing_state"], "no_feeds")

    def test_stale_or_revoked_or_deleted_sources_hide_the_whole_summary(self):
        self.generate()
        for field, invalid, valid in (("is_active", False, True), ("allow_ai_briefing", False, True)):
            Feed.objects.filter(pk=self.feed.pk).update(**{field: invalid})
            self.assertIsNone(briefing_context(timezone.now())["briefing"])
            Feed.objects.filter(pk=self.feed.pk).update(**{field: valid})
        for date in (self.now - timedelta(hours=25), self.now + timedelta(hours=1), None):
            Article.objects.filter(pk=self.article.pk).update(published_at=date)
            self.assertIsNone(briefing_context(timezone.now())["briefing"])
        Article.objects.filter(pk=self.article.pk).update(published_at=self.now)
        self.assertIsNotNone(briefing_context(timezone.now())["briefing"])
        self.article.delete()
        self.assertIsNone(briefing_context(timezone.now())["briefing"])

    def test_visiting_pages_does_not_generate_summary(self):
        with patch("news.llm_briefing.genai.Client") as client:
            self.client.get(reverse("news_feed"))
            self.client.get(reverse("home"))
        client.assert_not_called()

    def test_greeting_categories_and_summary_share_one_banner(self):
        self.generate()
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, 'class="feed-intro news-edition"', count=1)
        self.assertContains(response, 'id="edition-title"')
        self.assertContains(response, 'class="feed-edit-link" href="' + reverse("preferences") + '"', count=1)
        self.assertContains(response, "Síntesis de prueba")
        self.assertNotContains(response, 'class="editorial-collage"')


class EducationalFeedMigrationTests(TransactionTestCase):
    def test_forward_reverse_permissions_and_new_feed_defaults(self):
        previous = [("news", "0014_enable_mit_images")]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            feed_model = apps.get_model("news", "Feed")
            source, _ = apps.get_model("news", "Source").objects.get_or_create(name="Fuentes educativas")
            for url in import_module("news.migrations.0015_educational_feeds_and_briefing_status").FEEDS:
                feed_model.objects.get_or_create(url=url, defaults={"source": source, "name": "RSS"})
            feed_model.objects.update(etag="old-tag", last_modified="old-date")
            executor = MigrationExecutor(connection)
            target = executor.loader.graph.leaf_nodes()
            executor.migrate(target)
            apps = executor.loader.project_state(target).apps
            feed_model = apps.get_model("news", "Feed")
            self.assertEqual(feed_model.objects.filter(show_images=True, allow_ai_briefing=True, etag="", last_modified="").count(), 11)
            source = apps.get_model("news", "Source").objects.first()
            new_feed = feed_model.objects.create(source=source, name="Nuevo", url="https://example.com/new-feed")
            self.assertFalse(new_feed.show_images or new_feed.allow_ai_briefing)
            MigrationExecutor(connection).migrate(previous)
            self.assertEqual(feed_model.objects.filter(show_images=True).count(), 1)
            self.assertFalse(feed_model.objects.filter(allow_ai_briefing=True).exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
