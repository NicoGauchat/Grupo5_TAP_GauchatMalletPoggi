from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from news.category_aliases import category_slugs_for_entry
from news.ingestion import IngestionError, IngestionResult, permitted_summary
from news.management.commands.configure_argentine_sources import REVIEWED_FEEDS
from news.models import Article, Category, Feed


class ArgentineSourcesTests(TestCase):
    def test_preview_does_not_write_or_download(self):
        before = list(Feed.objects.order_by("pk").values())
        with patch("news.management.commands.configure_argentine_sources.ingest_feed") as download:
            call_command("configure_argentine_sources", stdout=StringIO())
        self.assertEqual(before, list(Feed.objects.order_by("pk").values()))
        download.assert_not_called()

    def test_apply_adds_exactly_three_known_media_and_preserves_elpais_and_articles(self):
        old_feed = Feed.objects.filter(source__name="EL PAÍS").first()
        article = Article.objects.create(feed=old_feed, title="Noticia ficticia conservada",
                                         original_url="https://example.test/conservada", published_at=timezone.now())
        before_count = Feed.objects.count()
        call_command("configure_argentine_sources", apply=True, stdout=StringIO())
        self.assertEqual(Feed.objects.count(), before_count + 3)
        self.assertTrue(Feed.objects.filter(source__name="EL PAÍS", is_active=True).exists())
        self.assertTrue(Article.objects.filter(pk=article.pk).exists())
        for name, _, _, url in REVIEWED_FEEDS:
            feed = Feed.objects.get(url=url)
            self.assertEqual(feed.source.name, name)
            self.assertTrue(feed.is_active and feed.show_summary and feed.allow_ai_briefing and feed.allow_ai_grouping)
            self.assertFalse(feed.show_images)
            self.assertEqual(list(feed.categories.values_list("slug", flat=True)), ["argentina"])

    def test_repeat_keeps_pauses_and_permissions_and_only_ingests_selected_media(self):
        call_command("configure_argentine_sources", apply=True, stdout=StringIO())
        paused = Feed.objects.get(url=REVIEWED_FEEDS[0][3])
        paused.is_active = paused.show_summary = paused.allow_ai_briefing = False
        paused.save()
        with patch("news.management.commands.configure_argentine_sources.ingest_feed", return_value=IngestionResult()) as download:
            call_command("configure_argentine_sources", apply=True, ingest=True, stdout=StringIO())
        self.assertEqual(download.call_count, 2)
        self.assertEqual({call.args[0].source.name for call in download.call_args_list}, {"La Capital", "El Ciudadano"})
        paused.refresh_from_db()
        self.assertFalse(paused.is_active or paused.show_summary or paused.allow_ai_briefing)

    def test_feed_failure_is_reported_and_others_still_run(self):
        with patch("news.management.commands.configure_argentine_sources.ingest_feed",
                   side_effect=[IngestionError("HTTP 503"), IngestionResult(), IngestionResult()]) as download:
            with self.assertRaisesMessage(CommandError, "Fallaron 1 RSS"):
                call_command("configure_argentine_sources", apply=True, ingest=True, stdout=StringIO(), stderr=StringIO())
        self.assertEqual(download.call_count, 3)

    def test_descriptions_are_short_clean_and_do_not_include_identified_third_parties(self):
        for name, _, _, url in REVIEWED_FEEDS:
            feed = SimpleNamespace(url=url, show_summary=True, source=SimpleNamespace(name=name))
            with self.subTest(name=name):
                self.assertEqual(permitted_summary({"summary": "<p>Bajada &amp; detalles ficticios.</p>"}, feed),
                                 "Bajada & detalles ficticios.")
                self.assertEqual(permitted_summary({"summary": "x" * 601}, feed), "")
                self.assertEqual(permitted_summary({"summary": "Bajada", "author": "Reuters"}, feed), "")

    def test_observed_section_labels_remain_scoped_to_their_feeds(self):
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Mundo"}]}, set(), "https://cenital.com/feed/"),
                         {"geopolitica"})
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Política"}]}, set(), "https://elciudadanoweb.com/feed/"),
                         {"politica-argentina", "argentina"})
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Política"}]}, set(), "https://example.test/rss"), set())

    def test_source_filter_classifies_only_selected_medium(self):
        call_command("configure_argentine_sources", apply=True, stdout=StringIO())
        for name, _, _, url in REVIEWED_FEEDS:
            Article.objects.create(feed=Feed.objects.get(url=url), title="Titular ficticio",
                                   original_url=f"{url}?ficticio=1", published_at=timezone.now())
        category = Category.objects.get(slug="argentina")
        def classify(batch, categories):
            self.assertEqual([article.feed.source.name for article in batch], ["Cenital"])
            return {article.pk: [category.slug] for article in batch}
        with patch("news.management.commands.classify_news_ai.classify_batch", side_effect=classify):
            call_command("classify_news_ai", source=["Cenital"], stdout=StringIO())
        self.assertEqual(Article.objects.filter(llm_classified_at__isnull=False).count(), 1)
