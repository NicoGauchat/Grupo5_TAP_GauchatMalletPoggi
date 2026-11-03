import json
from importlib import import_module
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone
from google.genai import errors

from .briefings import briefing_context
from .llm_briefing import BriefingError, summarize_articles
from .models import Article, Category, Feed, NewsBriefing, NewsBriefingItem, Source, Story, UserPreference


class BriefingResponseTests(SimpleTestCase):
    def setUp(self):
        categories = SimpleNamespace(all=lambda: [SimpleNamespace(slug="tecnologia", name="Tecnología")])
        self.article = SimpleNamespace(pk=7, title="Titular de prueba", published_at=timezone.now(),
            language="es", feed=SimpleNamespace(source=SimpleNamespace(name="Medio")),
            categories=categories, llm_categories=SimpleNamespace(all=lambda: []))

    def test_fixed_selection_restricts_schema_and_rejects_another_valid_category_article(self):
        other = SimpleNamespace(**{**vars(self.article), "pk": 8})
        rows = {"items": [{"category_slug": "tecnologia", "text": "Síntesis ficticia.",
                           "importance_score": 3, "article_ids": [7]}]}
        with patch("news.llm_briefing.api_key_for", return_value="ficticia"), patch(
                "news.llm_briefing._gemini_summary", return_value=rows) as provider, patch(
                "news.llm_briefing.backup_configured", return_value=False):
            summarize_articles([self.article, other], fixed_selection={"tecnologia": 7})
            schema = provider.call_args.args[1]["properties"]["items"]["properties"]["tecnologia"]
            self.assertEqual(schema["properties"]["article_ids"]["items"]["enum"], [7])
            rows["items"][0]["article_ids"] = [8]
            with self.assertRaisesRegex(BriefingError, "reason=fixed_selection"):
                summarize_articles([self.article, other], fixed_selection={"tecnologia": 7})

    def test_schema_requires_one_key_per_category_and_reports_missing_count(self):
        self.article.categories = SimpleNamespace(all=lambda: [
            SimpleNamespace(slug="tecnologia", name="Tecnología"),
            SimpleNamespace(slug="deportes", name="Deportes"),
        ])
        rows = [{"category_slug": slug, "text": "Síntesis ficticia de la categoría.",
                 "importance_score": 3, "article_ids": [7]} for slug in ("tecnologia", "deportes")]
        with patch("news.llm_briefing.api_key_for", return_value="ficticia"), patch(
            "news.llm_briefing._gemini_summary", side_effect=[{"items": rows}, {"items": rows[:1]}],
        ) as provider, patch("news.llm_briefing.backup_configured", return_value=False):
            self.assertEqual(len(summarize_articles([self.article])), 2)
            schema = provider.call_args.args[1]["properties"]["items"]
            self.assertEqual(schema["type"], "object")
            self.assertEqual(set(schema["required"]), {"tecnologia", "deportes"})
            self.assertFalse(schema["additionalProperties"])
            for row in schema["properties"].values():
                self.assertEqual(row["properties"]["article_ids"]["items"]["enum"], [7])
            with self.assertRaisesRegex(BriefingError, "reason=selection_count expected=2 received=1"):
                summarize_articles([self.article])

    def test_category_object_is_canonicalized_and_rejects_extra_missing_or_conflicting_fields(self):
        point = {"text": "Síntesis ficticia del acontecimiento.", "importance_score": 3, "article_ids": [7]}
        cases = [( {"tecnologia": point}, True), ({}, False),
                 ({"tecnologia": point, "deportes": point}, False),
                 ({"tecnologia": dict(point, category_slug="otra")}, False)]
        for items, valid in cases:
            with self.subTest(keys=list(items)), patch("news.llm_briefing.api_key_for", return_value="ficticia"), patch(
                "news.llm_briefing._gemini_summary", return_value={"items": items},
            ), patch("news.llm_briefing.backup_configured", return_value=False):
                if valid:
                    result = summarize_articles([self.article])
                    self.assertEqual(result[0]["category_slug"], "tecnologia")
                else:
                    with self.assertRaises(BriefingError):
                        summarize_articles([self.article])

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_rss_description_requires_both_permissions_and_remains_short_plain_text(self, client):
        client.return_value.models.generate_content.return_value.text = json.dumps({"items": [{
            "category_slug": "tecnologia", "text": "Síntesis redactada del hecho.", "importance_score": 3, "article_ids": [7],
        }]})
        cases = [(True, True, "<p>Detalle adicional &amp; verificado.</p>", "Detalle adicional & verificado."),
                 (False, True, "No autorizado", None), (True, False, "No autorizado", None),
                 (True, True, "x" * 601, None), (True, True, "", None)]
        for briefing, summary, description, expected in cases:
            self.article.feed.allow_ai_briefing = briefing
            self.article.feed.show_summary = summary
            self.article.summary = description
            with self.subTest(briefing=briefing, summary=summary, length=len(description)):
                result = summarize_articles([self.article])
                payload = json.loads(client.return_value.models.generate_content.call_args.kwargs["contents"].split("\n", 1)[1])
                self.assertEqual(payload["articles"][0].get("rss_description"), expected)
                self.assertEqual(result.description_count, int(expected is not None))

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_copied_headline_is_rejected_even_with_punctuation_or_case_changes(self, client):
        for text in (self.article.title, "  TITULAR DE PRUEBA. "):
            client.return_value.models.generate_content.return_value.text = json.dumps({"items": [{
                "category_slug": "tecnologia", "text": text, "importance_score": 3, "article_ids": [7],
            }]})
            with self.subTest(text=text), self.assertRaisesRegex(BriefingError, "reason=copied_headline"):
                summarize_articles([self.article])

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_comparison_receives_only_current_references_in_their_own_category(self, client):
        client.return_value.models.generate_content.return_value.text = json.dumps({"items": [{
            "category_slug": "tecnologia", "text": "Síntesis redactada del hecho.", "importance_score": 3, "article_ids": [7],
        }]})
        summarize_articles([self.article], previous_selection={"tecnologia": 7, "ciencia": 7, "argentina": 999})
        payload = json.loads(client.return_value.models.generate_content.call_args.kwargs["contents"].split("\n", 1)[1])
        self.assertEqual(payload["previous_selection"], {"tecnologia": 7})

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_validation_diagnostics_explain_field_without_echoing_response(self, client):
        row = {"category_slug": "tecnologia", "text": "private-summary", "importance_score": 4, "article_ids": [7]}
        cases = [(dict(row, category_slug="unknown-private-category"), "category"),
                 (dict(row, text="private-summary" * 50), "text"),
                 (dict(row, importance_score=True), "importance_score"),
                 (dict(row, article_ids=[9876543]), "article_id")]
        for invalid, reason in cases:
            client.return_value.models.generate_content.return_value.text = json.dumps({"items": [invalid]})
            with self.subTest(reason=reason), self.assertRaises(BriefingError) as caught:
                summarize_articles([self.article])
            self.assertIn(f"reason={reason}", str(caught.exception))
            self.assertNotIn("private-summary", str(caught.exception))
            self.assertNotIn("unknown-private-category", str(caught.exception))

    @patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
    @patch("news.llm_briefing.genai.Client")
    def test_validates_references_scores_and_duplicate_coverage(self, client):
        row = {"category_slug": "tecnologia", "text": "Síntesis de prueba", "importance_score": 4, "article_ids": [7]}
        for rows, valid in (([row], True), ([], False), ([dict(row, importance_score=3)], True),
                            ([dict(row, article_ids=[8])], False), ([row, row], False),
                            ([dict(row, article_ids=[7, 7])], False), ([dict(row, importance_score=True)], False)):
            client.return_value.models.generate_content.return_value.text = json.dumps({"items": rows})
            with self.subTest(rows=rows):
                if valid:
                    result = summarize_articles([self.article])
                    self.assertEqual(len(result), 1)
                else:
                    with self.assertRaises(BriefingError):
                        summarize_articles([self.article])
        options = client.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, 60_000)
        self.assertEqual(options.retry_options.attempts, 2)
        self.assertEqual(options.retry_options.http_status_codes, [500, 502, 503, 504])

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
    @patch("news.llm_briefing.genai.Client")
    def test_each_category_requires_a_single_reference_from_that_category(self, client):
        science = SimpleNamespace(pk=8, title="Anuncio científico ficticio", published_at=timezone.now(),
            language="es", feed=self.article.feed,
            categories=SimpleNamespace(all=lambda: [SimpleNamespace(slug="ciencia", name="Ciencia")]),
            llm_categories=SimpleNamespace(all=lambda: []))
        technology_row = {"category_slug": "tecnologia", "text": "Síntesis tecnológica.", "importance_score": 2, "article_ids": [7]}
        science_row = {"category_slug": "ciencia", "text": "Síntesis científica.", "importance_score": 3, "article_ids": [8]}
        generate = client.return_value.models.generate_content
        for rows in ([technology_row], [technology_row, technology_row],
                     [dict(technology_row, article_ids=[8]), science_row],
                     [dict(technology_row, article_ids=[7, 8]), science_row],
                     [dict(technology_row, category_slug="inventada"), science_row]):
            generate.return_value.text = json.dumps({"items": rows})
            with self.subTest(rows=rows), self.assertRaises(BriefingError):
                summarize_articles([self.article, science])
        generate.return_value.text = json.dumps({"items": [technology_row, science_row]})
        self.assertEqual(len(summarize_articles([self.article, science])), 2)
        self.assertNotIn("original_url", generate.call_args.kwargs["contents"])


@patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"})
class BriefingTests(TestCase):
    def setUp(self):
        Feed.objects.update(is_active=False)
        self.feed = Feed.objects.create(source=Source.objects.create(name="Medio del resumen"),
            name="RSS", url="https://example.com/briefing", is_active=True, allow_ai_briefing=True)
        self.now = timezone.now()
        self.article = Article.objects.create(feed=self.feed, title="Hecho relevante",
            original_url="https://example.com/news", published_at=self.now - timedelta(minutes=5))
        self.category = Category.objects.get(slug="tecnologia")
        self.article.llm_categories.add(self.category)
        self.user = get_user_model().objects.create_user("lector-resumen", password="prueba-local-segura")
        UserPreference.objects.create(user=self.user).categories.add(self.category)
        self.client.force_login(self.user)

    def generate(self, rows=None, **options):
        def response(*args, **kwargs):
            return rows if rows is not None else [
                {"category_slug": slug, "text": "Síntesis de prueba", "article_ids": [pk]}
                for slug, pk in kwargs["fixed_selection"].items()
            ]
        with patch("news.management.commands.generate_news_briefing.summarize_articles", side_effect=response) as summarize:
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

    def test_summary_and_category_ignore_a_higher_scored_rule_only_article(self):
        self.feed.allow_ai_grouping = True
        self.feed.save()
        self.article.story = Story.objects.create(importance_score=4)
        self.article.save()
        rule_only = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=5),
            title="Sólo regla editorial", original_url="https://example.com/rule-only", published_at=self.now)
        rule_only.categories.add(self.category)
        generation = self.generate()
        self.assertEqual(generation.call_args.kwargs["fixed_selection"], {self.category.slug: self.article.pk})
        legacy = NewsBriefing.objects.create(window_start=self.now - timedelta(hours=24))
        item = NewsBriefingItem.objects.create(briefing=legacy, category=self.category, position=1,
                                              text="Una síntesis anterior de clasificación mixta.")
        item.articles.add(rule_only)
        feed = self.client.get(reverse("news_feed"))
        reference = feed.context["category_briefings"][0]["reference"]
        first = self.client.get(reverse("category_news", args=[self.category.slug]),
                                {"period": "24h", "sort": "important"}).context["articles"][0]
        self.assertEqual(reference.pk, first.pk)
        self.assertContains(feed, '<h4 class="briefing-headline">')
        self.assertNotContains(feed, item.text)

    def test_summary_matches_24h_ranking_preserves_14d_and_invalidates_cache_on_new_winner(self):
        self.feed.allow_ai_grouping = True
        self.feed.save()
        self.article.story = Story.objects.create(importance_score=4)
        self.article.save()
        newer = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=2),
            title="Más reciente pero menor", original_url="https://example.com/latest-minor", published_at=self.now)
        older = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=5),
            title="Importante de la semana", original_url="https://example.com/older-major",
            published_at=self.now - timedelta(days=7))
        newer.llm_categories.add(self.category)
        older.llm_categories.add(self.category)
        generated = self.generate()
        self.assertEqual(generated.call_args.kwargs["fixed_selection"], {self.category.slug: self.article.pk})
        category_url = reverse("category_news", args=[self.category.slug])
        first_24h = self.client.get(category_url, {"sort": "important", "period": "24h"}).context["articles"][0]
        first_14d = self.client.get(category_url, {"sort": "important", "period": ""}).context["articles"][0]
        self.assertEqual(first_24h.pk, self.article.pk)
        self.assertEqual(first_14d.pk, older.pk)
        self.generate().assert_not_called()
        Story.objects.filter(pk=newer.story_id).update(importance_score=5)
        updated = self.generate()
        updated.assert_called_once()
        self.assertEqual(updated.call_args.kwargs["fixed_selection"], {self.category.slug: newer.pk})
        reference = briefing_context(timezone.now(), [self.category])["category_briefings"][0]["reference_id"]
        self.assertEqual(reference, self.client.get(category_url, {"sort": "important", "period": "24h"}).context["articles"][0].pk)

    def test_current_selection_keeps_a_candidate_slot_despite_250_newer_headlines(self):
        self.feed.allow_ai_grouping = True
        self.feed.save()
        self.article.story = Story.objects.create(importance_score=5)
        self.article.save()
        self.generate()
        Article.objects.bulk_create([Article(feed=self.feed, title=f"Hecho nuevo {i}",
            original_url=f"https://example.com/new/{i}", published_at=self.now) for i in range(250)])
        Article.llm_categories.through.objects.bulk_create([
            Article.llm_categories.through(article_id=pk, category_id=self.category.pk)
            for pk in Article.objects.exclude(pk=self.article.pk).values_list("pk", flat=True)
        ])
        summarize = self.generate(force=True)
        candidates = summarize.call_args.args[0]
        self.assertEqual(len(candidates), 1)
        self.assertIn(self.article.pk, {article.pk for article in candidates})
        self.assertEqual(summarize.call_args.kwargs["previous_selection"], {self.category.slug: self.article.pk})
        self.assertEqual(NewsBriefing.objects.first().items.get().articles.get().pk, self.article.pk)

    def test_expired_selection_is_removed_while_other_category_keeps_its_candidate(self):
        category, science = self.add_science()
        rows = [{"category_slug": self.category.slug, "text": "Tecnología.", "article_ids": [self.article.pk]},
                {"category_slug": category.slug, "text": "Ciencia.", "article_ids": [science.pk]}]
        self.generate(rows=rows)
        Article.objects.filter(pk=self.article.pk).update(published_at=self.now - timedelta(hours=25))
        summarize = self.generate(rows=[rows[1]], force=True)
        self.assertEqual(summarize.call_args.kwargs["previous_selection"], {category.slug: science.pk})
        self.assertNotIn(self.article.pk, {article.pk for article in summarize.call_args.args[0]})

    def test_new_choice_replaces_previous_and_becomes_next_comparison_reference(self):
        self.generate()
        newer = Article.objects.create(feed=self.feed, title="Otro hecho relevante",
            original_url="https://example.com/new-winner", published_at=self.now)
        newer.llm_categories.add(self.category)
        rows = [{"category_slug": self.category.slug, "text": "Síntesis del nuevo hecho.", "article_ids": [newer.pk]}]
        first = self.generate(rows=rows, force=True)
        self.assertEqual(first.call_args.kwargs["previous_selection"], {self.category.slug: self.article.pk})
        self.assertEqual(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["reference_id"], newer.pk)
        second = self.generate(rows=rows, force=True)
        self.assertEqual(second.call_args.kwargs["previous_selection"], {self.category.slug: newer.pk})

    def test_empty_success_is_cached(self):
        self.article.delete()
        self.generate(rows=[])
        self.generate().assert_not_called()
        self.assertEqual(NewsBriefing.objects.first().status, "empty")
        self.assertContains(self.client.get(reverse("news_feed")), "Sin titulares habilitados")

    def test_failure_preserves_previous_valid_result_and_logs_safe_code(self):
        self.generate()
        with patch("news.management.commands.generate_news_briefing.summarize_articles",
                   side_effect=BriefingError("La cuota no está disponible.", "quota")), self.assertRaises(CommandError):
            call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual((NewsBriefing.objects.first().status, NewsBriefing.objects.first().error_code), ("error", "quota"))
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, "No se pudo actualizar")
        self.assertContains(response, "Síntesis de prueba")

    def test_ties_choose_latest_id_and_only_the_selected_reference_is_sent(self):
        Article.objects.bulk_create([Article(feed=self.feed, title=f"Titular {i}",
            original_url=f"https://example.com/batch/{i}", published_at=self.article.published_at) for i in range(255)])
        Article.llm_categories.through.objects.bulk_create([
            Article.llm_categories.through(article_id=pk, category_id=self.category.pk)
            for pk in Article.objects.values_list("pk", flat=True) if pk != self.article.pk
        ])
        for label, date in (("old", self.now - timedelta(hours=25)), ("future", self.now + timedelta(hours=1))):
            Article.objects.create(feed=self.feed, title=label, original_url=f"https://example.com/{label}", published_at=date)
        expected = list(Article.objects.filter(published_at=self.article.published_at).order_by("-id").values_list("pk", flat=True)[:1])
        summarize = self.generate(rows=[])
        self.assertEqual([article.pk for article in summarize.call_args.args[0]], expected)
        self.assertEqual(NewsBriefing.objects.first().article_count, 1)

    def test_no_sources_no_articles_and_missing_key_have_distinct_states(self):
        self.assertEqual(briefing_context(self.now, [self.category])["category_briefings"][0]["state"], "pending")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEY_SECONDARY": ""}):
            with self.assertRaises(CommandError):
                call_command("generate_news_briefing", stdout=StringIO())
            self.assertEqual(NewsBriefing.objects.first().error_code, "missing_key")
            self.assertEqual(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["state"], "error")
            self.assertNotContains(self.client.get(reverse("news_feed")), "todavía no está configurado")
        Article.objects.all().delete()
        call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual(NewsBriefing.objects.first().error_code, "no_articles")
        self.assertEqual(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["state"], "no_articles")
        self.feed.allow_ai_briefing = False
        self.feed.save()
        call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual(NewsBriefing.objects.first().error_code, "no_feeds")
        self.assertEqual(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["state"], "no_articles")

    def test_stale_or_revoked_or_deleted_sources_hide_the_whole_summary(self):
        self.generate()
        for field, invalid, valid in (("is_active", False, True), ("allow_ai_briefing", False, True)):
            Feed.objects.filter(pk=self.feed.pk).update(**{field: invalid})
            self.assertIsNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["item"])
            Feed.objects.filter(pk=self.feed.pk).update(**{field: valid})
        for date in (self.now - timedelta(hours=25), self.now + timedelta(hours=1), None):
            Article.objects.filter(pk=self.article.pk).update(published_at=date)
            self.assertIsNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["item"])
        Article.objects.filter(pk=self.article.pk).update(published_at=self.now)
        self.assertIsNotNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["item"])
        self.article.delete()
        self.assertIsNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["item"])

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

    def add_science(self):
        category = Category.objects.get(slug="ciencia")
        article = Article.objects.create(feed=self.feed, title="Titular científico sintético",
            original_url="https://example.com/science", published_at=self.now - timedelta(minutes=2))
        article.llm_categories.add(category)
        self.user.news_preference.categories.add(category)
        return category, article

    def test_ai_text_is_persisted_per_category_and_visible_without_a_web_api_key(self):
        category, article = self.add_science()
        rows = [{"category_slug": self.category.slug, "text": "La IA explica la noticia tecnológica.", "article_ids": [self.article.pk]},
                {"category_slug": category.slug, "text": "La IA resume el anuncio científico.", "article_ids": [article.pk]}]
        self.generate(rows=rows)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEY_SECONDARY": ""}), patch("news.llm_briefing.genai.Client") as model:
            response = self.client.get(reverse("news_feed"))
            model.assert_not_called()
        self.assertEqual(len(response.context["category_briefings"]), 2)
        self.assertContains(response, rows[0]["text"])
        self.assertContains(response, rows[1]["text"])
        self.assertContains(response, f'href="{article.original_url}" target="_blank" rel="noopener"')
        self.assertContains(response, "Base de la síntesis", count=2)
        self.assertNotContains(response, "no está configurado")
        self.assertEqual(set(NewsBriefingItem.objects.values_list("category_id", flat=True)), {self.category.pk, category.pk})
        self.user.news_preference.categories.remove(category)
        response = self.client.get(reverse("news_feed"))
        self.assertNotContains(response, rows[1]["text"])
        self.assertEqual(NewsBriefingItem.objects.filter(category=category).count(), 1)

    def test_summary_sources_only_include_distinct_current_verified_coverages(self):
        self.feed.allow_ai_grouping = True
        self.feed.save()
        story = Story.objects.create()
        self.article.story = story
        self.article.save()
        source = Source.objects.create(name="Otra fuente", license_url="https://example.com/license")
        feed = Feed.objects.create(source=source, name="Coberturas", url="https://example.com/coverage/rss",
                                   is_active=True, allow_ai_grouping=True, allow_ai_briefing=False)

        def coverage(label, **kwargs):
            return Article.objects.create(feed=feed, story=story, title=label,
                original_url=f"https://example.com/coverage/{label}",
                published_at=kwargs.pop("published_at", self.now - timedelta(minutes=1)), **kwargs)

        other = coverage("otra", byline="Autor de ensayo")
        coverage("duplicada", published_at=self.now - timedelta(hours=2))
        old = coverage("antigua", published_at=self.now - timedelta(hours=25))
        future = coverage("futura", published_at=self.now + timedelta(hours=2))
        unrelated = coverage("otro-hecho")
        unrelated.story = Story.objects.create()
        unrelated.save()
        self.generate()
        response = self.client.get(reverse("news_feed"))
        row = response.context["category_briefings"][0]
        self.assertEqual(row["source_count"], 2)
        self.assertEqual({a.pk for a in row["sources"]}, {self.article.pk, other.pk})
        self.assertContains(response, other.original_url)
        self.assertContains(response, "Otra cobertura del mismo hecho")
        self.assertContains(response, "Autor de ensayo")
        self.assertContains(response, source.license_url)
        for excluded in (old, future, unrelated):
            self.assertNotContains(response, excluded.original_url)
        for field in ("is_active", "allow_ai_grouping"):
            with self.subTest(field=field):
                setattr(feed, field, False)
                feed.save()
                self.assertEqual(briefing_context(self.now, [self.category])["category_briefings"][0]["source_count"], 1)
                setattr(feed, field, True)
                feed.save()
        Story.objects.filter(pk=story.pk).update(grouping_version=0)
        self.assertEqual(briefing_context(self.now, [self.category])["category_briefings"][0]["source_count"], 1)

    def test_briefing_image_prefers_reference_and_respects_revoked_permission(self):
        self.feed.show_images = True
        self.feed.save()
        self.article.image_url = "https://example.com/reference.jpg"
        self.article.image_credit = "Fotografía del medio"
        self.article.save()
        self.generate()

        response = self.client.get(reverse("news_feed"))
        row = response.context["category_briefings"][0]
        self.assertEqual(row["image_article"].pk, self.article.pk)
        self.assertContains(response, 'src="https://example.com/reference.jpg"')
        self.assertContains(response, "Fotografía del medio")
        self.assertContains(response, f'href="{self.article.original_url}" target="_blank" rel="noopener"')

        self.feed.show_images = False
        self.feed.save()
        response = self.client.get(reverse("news_feed"))
        row = response.context["category_briefings"][0]
        self.assertIsNone(row["image_article"])
        self.assertNotContains(response, "https://example.com/reference.jpg")
        self.assertNotContains(response, f'src="/static/{row["fallback_image"]}"')

    def test_briefing_image_uses_only_current_verified_coverage(self):
        self.feed.allow_ai_grouping = True
        self.feed.save()
        story = Story.objects.create()
        self.article.story = story
        self.article.save()
        source = Source.objects.create(name="Cobertura con foto")
        feed = Feed.objects.create(source=source, name="RSS", url="https://example.com/photo/rss",
                                   is_active=True, allow_ai_grouping=True, show_images=True)
        coverage = Article.objects.create(feed=feed, story=story, title="Mismo acontecimiento",
            original_url="https://example.com/coverage/photo", published_at=self.now - timedelta(minutes=1),
            image_url="https://example.com/coverage.jpg", image_credit="Crédito de cobertura")
        unrelated = Article.objects.create(feed=feed, story=Story.objects.create(), title="Otro acontecimiento",
            original_url="https://example.com/unrelated", published_at=self.now,
            image_url="https://example.com/unrelated.jpg")
        self.generate()

        response = self.client.get(reverse("news_feed"))
        row = response.context["category_briefings"][0]
        self.assertEqual(row["image_article"].pk, coverage.pk)
        self.assertContains(response, f'href="{coverage.original_url}" target="_blank" rel="noopener"')
        self.assertContains(response, "Crédito de cobertura")
        self.assertNotContains(response, unrelated.image_url)

        Story.objects.filter(pk=story.pk).update(grouping_version=0)
        response = self.client.get(reverse("news_feed"))
        self.assertIsNone(response.context["category_briefings"][0]["image_article"])
        self.assertNotContains(response, coverage.image_url)
        Story.objects.filter(pk=story.pk).update(grouping_version=1)

        feed.show_images = False
        feed.save()
        self.assertIsNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["image_article"])
        feed.show_images = True
        feed.is_active = False
        feed.save()
        self.assertIsNone(briefing_context(timezone.now(), [self.category])["category_briefings"][0]["image_article"])

    def test_category_photo_uses_next_important_story_without_repeating_briefing(self):
        self.feed.allow_ai_grouping = True
        self.feed.show_images = True
        self.feed.save()
        self.article.story = Story.objects.create(importance_score=5)
        self.article.image_url = "https://example.com/summary.jpg"
        self.article.save()

        def featured(label, score, image_url):
            article = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=score),
                title=label, original_url=f"https://example.com/{label}",
                published_at=self.now - timedelta(minutes=1), image_url=image_url,
                image_credit=f"Crédito {label}")
            article.llm_categories.add(self.category)
            return article

        repeated_photo = featured("repetida", 4, self.article.image_url)
        chosen = featured("alternativa", 3, "")
        chosen_coverage = Article.objects.create(feed=self.feed, story=chosen.story,
            title="Otra cobertura de la alternativa", original_url="https://example.com/alternative/photo",
            published_at=self.now, image_url="https://example.com/alternative.jpg",
            image_credit="Crédito alternativa")
        self.generate()

        response = self.client.get(reverse("news_feed"))
        section = response.context["sections"][0]
        self.assertEqual(section["photo_article"].pk, chosen_coverage.pk)
        self.assertContains(response, f'src="{chosen_coverage.image_url}"')
        self.assertContains(response, f'href="{chosen_coverage.original_url}" target="_blank" rel="noopener"')
        self.assertContains(response, f'class="topic-card-link" href="{reverse("category_news", args=[self.category.slug])}"')
        self.assertNotContains(response, repeated_photo.original_url)
        self.assertContains(response, "Crédito alternativa")

        self.feed.show_images = False
        self.feed.save()
        response = self.client.get(reverse("news_feed"))
        self.assertIsNone(response.context["sections"][0]["photo_article"])
        self.assertNotContains(response, chosen_coverage.image_url)
        self.assertContains(response, "Imagen ilustrativa")

    def test_category_photo_needs_current_scored_story_and_ignores_legacy_mode(self):
        self.feed.allow_ai_grouping = True
        self.feed.show_images = True
        self.feed.save()
        self.generate()

        def candidate(label, *, minutes=1, scored=True):
            article = Article.objects.create(feed=self.feed,
                story=Story.objects.create(importance_score=4 if scored else None), title=label,
                original_url=f"https://example.com/{label}", published_at=self.now - timedelta(minutes=minutes),
                image_url=f"https://example.com/{label}.jpg")
            return article

        ai_only = candidate("solo-ia")
        ai_only.llm_categories.add(self.category)
        old = candidate("vencida", minutes=25 * 60)
        old.llm_categories.add(self.category)
        unscored = candidate("sin-puntaje", scored=False)
        unscored.llm_categories.add(self.category)

        preference = self.user.news_preference
        preference.classification_mode = "rules"
        preference.save()
        self.assertEqual(self.client.get(reverse("news_feed")).context["sections"][0]["photo_article"].pk, ai_only.pk)

        preference.classification_mode = UserPreference.CLASSIFICATION_AI
        preference.save()
        response = self.client.get(reverse("news_feed"))
        self.assertEqual(response.context["sections"][0]["photo_article"].pk, ai_only.pk)
        self.assertNotContains(response, old.image_url)
        self.assertNotContains(response, unscored.image_url)

        Story.objects.filter(pk=ai_only.story_id).update(grouping_version=0)
        self.assertIsNone(self.client.get(reverse("news_feed")).context["sections"][0]["photo_article"])

    def test_category_cards_do_not_repeat_a_photo_across_categories(self):
        science, science_reference = self.add_science()
        self.feed.allow_ai_grouping = True
        self.feed.show_images = True
        self.feed.save()
        self.generate(rows=[
            {"category_slug": self.category.slug, "text": "Síntesis tecnológica.", "article_ids": [self.article.pk]},
            {"category_slug": science.slug, "text": "Síntesis científica.", "article_ids": [science_reference.pk]},
        ])
        shared = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=5),
            title="Acontecimiento de dos categorías", original_url="https://example.com/shared",
            published_at=self.now, image_url="https://example.com/shared.jpg")
        shared.llm_categories.add(self.category, science)
        alternative = Article.objects.create(feed=self.feed, story=Story.objects.create(importance_score=4),
            title="Otro hecho tecnológico", original_url="https://example.com/technology/second",
            published_at=self.now, image_url="https://example.com/second.jpg")
        alternative.llm_categories.add(self.category)
        sections = self.client.get(reverse("news_feed")).context["sections"]
        photos = {section["category"].slug: section["photo_article"] for section in sections}
        self.assertEqual(photos[science.slug].pk, shared.pk)
        self.assertEqual(photos[self.category.slug].pk, alternative.pk)
        self.assertEqual(len({photo.image_url for photo in photos.values()}), 2)

    def test_expired_category_does_not_hide_another_valid_ai_summary(self):
        category, article = self.add_science()
        self.generate(rows=[{"category_slug": self.category.slug, "text": "Síntesis que vencerá.", "article_ids": [self.article.pk]},
                            {"category_slug": category.slug, "text": "Síntesis científica vigente.", "article_ids": [article.pk]}])
        Article.objects.filter(pk=self.article.pk).update(published_at=self.now - timedelta(hours=25))
        response = self.client.get(reverse("news_feed"))
        self.assertNotContains(response, "Síntesis que vencerá.")
        self.assertContains(response, "Síntesis científica vigente.")

    def test_pending_summary_never_falls_back_to_a_title_or_local_selection(self):
        with patch("news.llm_briefing.genai.Client") as model:
            response = self.client.get(reverse("news_feed"))
            model.assert_not_called()
        self.assertContains(response, "El resumen IA está pendiente de generación.")
        self.assertNotContains(response, "Ver fuentes y fechas de los resúmenes")
        self.assertNotContains(response, self.article.title)
        self.assertNotContains(response, "Más reciente · importancia pendiente")

    def test_new_category_invalidates_a_recent_incomplete_cache(self):
        self.generate()
        category, article = self.add_science()
        model = self.generate(rows=[{"category_slug": self.category.slug, "text": "Tecnología.", "article_ids": [self.article.pk]},
                                    {"category_slug": category.slug, "text": "Ciencia.", "article_ids": [article.pk]}])
        model.assert_called_once()

    def test_inputs_reserve_space_for_less_frequent_categories_and_respect_permissions(self):
        category, science = self.add_science()
        Article.objects.bulk_create([Article(feed=self.feed, title=f"Titular tecnológico {i}",
            original_url=f"https://example.com/dense/{i}", published_at=self.now) for i in range(260)])
        Article.llm_categories.through.objects.bulk_create([
            Article.llm_categories.through(article_id=pk, category_id=self.category.pk)
            for pk in Article.objects.exclude(pk__in=[self.article.pk, science.pk]).values_list("pk", flat=True)
        ])
        excluded_feed = Feed.objects.create(source=self.feed.source, name="Sin síntesis", url="https://example.com/forbidden/rss",
                                             is_active=True, allow_ai_briefing=False)
        forbidden = Article.objects.create(feed=excluded_feed, title="No transmitir este titular",
            original_url="https://example.com/forbidden", published_at=self.now)
        forbidden.llm_categories.add(category)
        model = self.generate(rows=[])
        sent = model.call_args.args[0]
        self.assertEqual(len(sent), 2)
        self.assertIn(science.pk, {article.pk for article in sent})
        self.assertNotIn(forbidden.pk, {article.pk for article in sent})




class CategoryBriefingMigrationTests(TransactionTestCase):
    def test_category_migration_preserves_legacy_summaries_and_reverses(self):
        previous = [("news", "0019_story_grouping_version")]
        target = [("news", "0020_newsbriefingitem_category")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(previous)
            old = executor.loader.project_state(previous).apps
            source = old.get_model("news", "Source").objects.create(name="Medio sintético migración resumen")
            feed = old.get_model("news", "Feed").objects.create(source_id=source.pk, name="RSS", url="https://example.com/migrate-briefing/rss")
            article = old.get_model("news", "Article").objects.create(feed_id=feed.pk, title="Titular previo",
                original_url="https://example.com/migrate-briefing/article")
            briefing = old.get_model("news", "NewsBriefing").objects.create(window_start=timezone.now())
            item = old.get_model("news", "NewsBriefingItem").objects.create(briefing_id=briefing.pk, position=1, text="Síntesis anterior.")
            item.articles.add(article)
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            ItemModel = current.get_model("news", "NewsBriefingItem")
            stored = ItemModel.objects.get(pk=item.pk)
            self.assertIsNone(stored.category_id)
            self.assertEqual(stored.articles.get().pk, article.pk)
            category = current.get_model("news", "Category").objects.get(slug="ciencia")
            ItemModel.objects.create(briefing_id=briefing.pk, category_id=category.pk, position=2, text="Síntesis por categoría.")
            with self.assertRaises(IntegrityError), transaction.atomic():
                ItemModel.objects.create(briefing_id=briefing.pk, category_id=category.pk, position=3, text="No duplicar.")
            executor = MigrationExecutor(connection)
            executor.migrate(previous)
            restored = executor.loader.project_state(previous).apps
            self.assertEqual(restored.get_model("news", "NewsBriefingItem").objects.get(pk=item.pk).text, "Síntesis anterior.")
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())


class OnlyAIPreferenceMigrationTests(TransactionTestCase):
    def test_existing_modes_are_normalized_without_losing_categories_and_reverse_remains_valid(self):
        previous = [("news", "0020_newsbriefingitem_category")]
        target = [("news", "0021_solo_clasificacion_ia")]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            old = executor.loader.project_state(previous).apps
            category = old.get_model("news", "Category").objects.create(name="Categoría de migración", slug="migration-ai")
            ids = []
            for index, mode in enumerate(("both", "rules", "ai")):
                user = old.get_model("auth", "User").objects.create(username=f"migration-ai-{index}")
                preference = old.get_model("news", "UserPreference").objects.create(user_id=user.pk, classification_mode=mode)
                preference.categories.add(category)
                ids.append(preference.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            preferences = current.get_model("news", "UserPreference").objects.filter(pk__in=ids)
            self.assertEqual(list(preferences.values_list("classification_mode", flat=True)), ["ai"] * 3)
            for preference in preferences:
                self.assertEqual(list(preference.categories.values_list("pk", flat=True)), [category.pk])
            MigrationExecutor(connection).migrate(previous)
            self.assertEqual(old.get_model("news", "UserPreference").objects.filter(pk__in=ids, classification_mode="ai").count(), 3)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())


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
