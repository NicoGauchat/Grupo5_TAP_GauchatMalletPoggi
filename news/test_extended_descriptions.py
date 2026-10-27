from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from news.ingestion import LOSANDES_DESCRIPTION_FEEDS, NASA_DESCRIPTION_FEED, NASA_USAGE_POLICY, permitted_summary
from news.llm_briefing import BriefingError, NASA_AI_NOTICE, summarize_articles
from news.models import Article, Feed, Story


class ExtendedDescriptionPolicyTests(SimpleTestCase):
    def nasa_feed(self):
        return SimpleNamespace(url=NASA_DESCRIPTION_FEED, show_summary=True, allow_ai_briefing=True,
                               source=SimpleNamespace(name="NASA", license_url=NASA_USAGE_POLICY))

    def test_nasa_and_losandes_summaries_are_short_and_reject_third_party_signals(self):
        for feed in (self.nasa_feed(), SimpleNamespace(url=LOSANDES_DESCRIPTION_FEEDS[0], show_summary=True,
                                                       source=SimpleNamespace(name="Los Andes"))):
            with self.subTest(source=feed.source.name):
                self.assertEqual(permitted_summary({"summary": "<p>Bajada &amp; detalles ficticios.</p>"}, feed),
                                 "Bajada & detalles ficticios.")
                for entry in ({"summary": "x" * 601}, {"summary": "Texto", "author": "Reuters"},
                              {"summary": "Texto", "copyright": "Copyright tercera parte"}):
                    self.assertEqual(permitted_summary(entry, feed), "")
        feed = self.nasa_feed()
        feed.source.license_url = ""
        self.assertEqual(permitted_summary({"summary": "Bajada"}, feed), "")

    def test_nasa_briefing_uses_description_and_adds_notice_for_both_providers(self):
        category = SimpleNamespace(slug="tecnologia", name="Tecnología")
        article = SimpleNamespace(pk=1, title="Titular ficticio", published_at=timezone.now(), language="en",
                                  summary="Bajada científica ficticia.", byline="", feed=self.nasa_feed(),
                                  categories=SimpleNamespace(all=lambda: [category]),
                                  llm_categories=SimpleNamespace(all=lambda: []))
        result = {"items": [{"category_slug": "tecnologia", "importance_score": 3,
                             "article_ids": [1], "text": "Se presentó un prototipo ficticio para una investigación."}]}
        for backup in (False, True):
            with self.subTest(backup=backup), patch("news.llm_briefing.api_key_for", return_value="ficticia"), patch(
                "news.llm_briefing._gemini_summary", return_value=result,
                side_effect=BriefingError("Cuota", "quota") if backup else None,
            ) as primary, patch("news.llm_briefing.backup_configured", return_value=True), patch(
                "news.llm_briefing.backup_providers", return_value=["groq"],
            ), patch("news.llm_briefing.request_backup", return_value=result):
                items = summarize_articles([article])
                self.assertTrue(items[0]["text"].endswith(NASA_AI_NOTICE))
                self.assertLessEqual(len(items[0]["text"]), 450)
                self.assertEqual(items.description_count, 1)
                self.assertIn("rss_description", primary.call_args.args[0])

    def test_nasa_invalid_attribution_or_overlong_notice_rejects_result(self):
        category = SimpleNamespace(slug="tecnologia", name="Tecnología")
        article = SimpleNamespace(pk=1, title="Titular", published_at=timezone.now(), language="en", summary="Bajada",
                                  feed=self.nasa_feed(), categories=SimpleNamespace(all=lambda: [category]),
                                  llm_categories=SimpleNamespace(all=lambda: []))
        for text in ("Según NASA, este texto está comprobado.", "According to NASA, verified.", "x" * 450):
            result = {"items": [{"category_slug": "tecnologia", "importance_score": 3,
                                 "article_ids": [1], "text": text}]}
            with self.subTest(text_length=len(text)), patch("news.llm_briefing.api_key_for", return_value="ficticia"), patch(
                "news.llm_briefing._gemini_summary", return_value=result,
            ), patch("news.llm_briefing.backup_configured", return_value=False), self.assertRaises(BriefingError):
                summarize_articles([article])


class ExtendedDescriptionActivationTests(TestCase):
    def test_expressly_restricted_source_stays_out_of_all_ai_stages(self):
        feed = Feed.objects.filter(source__name="EL PAÍS").first()
        feed.is_active = feed.allow_ai_grouping = feed.allow_ai_briefing = feed.show_summary = True
        feed.save()
        for index, story in enumerate((None, Story.objects.create())):
            article = Article.objects.create(feed=feed, title="Titular ficticio restringido",
                                             original_url=f"https://example.test/restricted/{index}",
                                             published_at=timezone.now(), story=story)
            article.categories.add(feed.categories.first())
        for command, target in (("classify_news_ai", "news.management.commands.classify_news_ai.classify_batch"),
                                ("group_news_ai", "news.management.commands.group_news_ai.group_articles"),
                                ("score_news_ai", "news.management.commands.score_news_ai.score_stories")):
            module = command
            with self.subTest(command=command), patch(target) as provider, patch(
                f"news.management.commands.{module}.AI_EXCLUDED_SOURCES", ("EL PAÍS",),
            ):
                call_command(command, stdout=StringIO())
                provider.assert_not_called()
        with patch("news.management.commands.generate_news_briefing.summarize_articles", return_value=[]) as provider, patch(
            "news.management.commands.generate_news_briefing.AI_EXCLUDED_SOURCES", ("EL PAÍS",),
        ):
            call_command("generate_news_briefing", force=True, stdout=StringIO())
        self.assertEqual(provider.call_args.args[0], [])
        self.assertEqual(Article.objects.filter(feed=feed).count(), 2)

    def test_all_activation_revokes_restricted_ai_flags_but_preserves_rss(self):
        active_before = dict(Feed.objects.filter(source__name="EL PAÍS").values_list("pk", "is_active"))
        with patch("news.management.commands.refresh_briefing_descriptions.AI_EXCLUDED_SOURCES", ("EL PAÍS",)), patch("news.management.commands.refresh_briefing_descriptions.ingest_feed", return_value=SimpleNamespace(
            created=0, duplicates=0,
        )):
            call_command("refresh_briefing_descriptions", source="all", enable_reviewed=True, stdout=StringIO())
        for feed in Feed.objects.filter(source__name="EL PAÍS"):
            self.assertFalse(feed.allow_ai_grouping or feed.allow_ai_briefing or feed.show_summary)
            self.assertEqual(feed.is_active, active_before[feed.pk])

    def test_all_briefing_activation_restores_elpais_and_does_not_reactivate_other_paused_feeds(self):
        Feed.objects.filter(source__name="EL PAÍS").update(is_active=False, allow_ai_briefing=False, show_summary=False)
        paused = Feed.objects.get(url=NASA_DESCRIPTION_FEED)
        paused.is_active = False
        paused.show_summary = paused.allow_ai_briefing = False
        paused.save()
        before = list(Feed.objects.order_by("pk").values())
        call_command("enable_news_briefing", stdout=StringIO())
        self.assertEqual(before, list(Feed.objects.order_by("pk").values()))
        call_command("enable_news_briefing", apply=True, stdout=StringIO())
        self.assertFalse(Feed.objects.filter(is_active=True, allow_ai_briefing=False).exists())
        self.assertFalse(Feed.objects.filter(is_active=True, show_summary=False).exists())
        self.assertFalse(Feed.objects.filter(source__name="EL PAÍS", is_active=False).exists())
        paused.refresh_from_db()
        self.assertFalse(paused.is_active or paused.show_summary or paused.allow_ai_briefing)

    def test_explicit_activation_only_changes_selected_active_reviewed_feed(self):
        feed = Feed.objects.get(url=NASA_DESCRIPTION_FEED)
        before = list(Feed.objects.exclude(pk=feed.pk).order_by("pk").values())
        with patch("news.management.commands.refresh_briefing_descriptions.ingest_feed", return_value=SimpleNamespace(
            created=0, duplicates=0,
        )) as ingest:
            call_command("refresh_briefing_descriptions", source="nasa", enable_reviewed=True, stdout=StringIO())
            ingest.assert_called_once()
        feed.refresh_from_db()
        self.assertTrue(feed.show_summary and feed.allow_ai_briefing)
        self.assertEqual(feed.source.license_url, NASA_USAGE_POLICY)
        self.assertEqual(before, list(Feed.objects.exclude(pk=feed.pk).order_by("pk").values()))

    def test_paused_nasa_is_not_reactivated_and_losandes_is_explicit(self):
        Feed.objects.filter(url=NASA_DESCRIPTION_FEED).update(is_active=False)
        with self.assertRaises(CommandError):
            call_command("refresh_briefing_descriptions", source="nasa", enable_reviewed=True, stdout=StringIO())
        with patch("news.management.commands.refresh_briefing_descriptions.ingest_feed", return_value=SimpleNamespace(
            created=0, duplicates=0,
        )) as ingest:
            call_command("refresh_briefing_descriptions", source="losandes", enable_reviewed=True, stdout=StringIO())
        self.assertEqual(ingest.call_count, 3)
        self.assertFalse(Feed.objects.filter(url__in=LOSANDES_DESCRIPTION_FEEDS, show_summary=False).exists())
