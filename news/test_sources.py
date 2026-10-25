from importlib import import_module
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from .category_aliases import category_slugs_for_entry
from .ingestion import ingest_feed
from .llm_classification import CATEGORY_DESCRIPTIONS
from .models import Article, Category, Feed


class ExpandedSourceTests(TestCase):
    def test_three_new_categories_and_reviewed_feeds_without_brazilian_agency(self):
        self.assertEqual(Category.objects.count(), 11)
        self.assertEqual(Feed.objects.filter(is_active=True).count(), 26)
        self.assertFalse(Feed.objects.filter(source__name="Agência Brasil").exists())
        for slug in ("salud", "medioambiente", "deportes"):
            self.assertIn(slug, CATEGORY_DESCRIPTIONS)
            self.assertTrue(Category.objects.filter(slug=slug, feeds__is_active=True).exists())
        catalog = import_module("news.migrations.0018_expand_categories_and_sources")
        feeds = Feed.objects.filter(url__in=[item[4] for item in catalog.FEEDS])
        self.assertEqual(feeds.count(), 15)
        self.assertFalse(feeds.filter(show_images=True).exists())
        self.assertFalse(feeds.filter(show_summary=True).exists())
        self.assertFalse(feeds.filter(allow_ai_briefing=True).exists())
        self.assertEqual(feeds.filter(allow_ai_grouping=True).count(), 15)

    def test_new_labels_are_exact_and_nasa_aliases_are_scoped(self):
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Salud pública"}]}, []), {"salud"})
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Medio ambiente"}]}, []), {"medioambiente"})
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Deportes"}]}, []), {"deportes"})
        entry = {"tags": [{"term": "Earth Science"}]}
        self.assertEqual(category_slugs_for_entry(entry, [], "https://www.nasa.gov/technology/feed/"), {"ciencia", "medioambiente"})
        self.assertEqual(category_slugs_for_entry(entry, []), set())
        self.assertEqual(category_slugs_for_entry({"tags": [{"term": "Etiqueta no temática"}]}, [],
                                                "https://www.eldiario.es/rss/internacional/"), {"geopolitica"})

    def test_author_license_and_original_credit_survive_ingestion_updates(self):
        feed = Feed.objects.get(url="https://www.eldiario.es/rss/internacional/")
        entry = {"title": "Titular sintético", "link": "https://example.com/source-credit", "id": "credit-1",
                 "published_parsed": timezone.now().utctimetuple(), "author": "<b>Autor de ensayo</b>",
                 "summary": "Cuerpo que no debe guardarse", "media_thumbnail": [{"url": "https://example.com/photo.jpg"}]}
        with patch("news.ingestion.download_feed", return_value=([entry], "", "")):
            ingest_feed(feed)
        article = Article.objects.get(original_url=entry["link"])
        self.assertEqual(article.byline, "Autor de ensayo")
        self.assertEqual(feed.source.license_url, "https://creativecommons.org/licenses/by-nc/4.0/")
        self.assertEqual(article.summary, "")
        self.assertEqual(article.image_url, "")
        entry.pop("author")
        with patch("news.ingestion.download_feed", return_value=([entry], "", "")):
            ingest_feed(feed)
        article.refresh_from_db()
        self.assertEqual(article.byline, "Autor de ensayo")


class ImportanceMigrationTests(TransactionTestCase):
    def test_upgrade_and_reverse_keep_original_articles_and_user_configuration(self):
        previous = [("news", "0016_story_feed_allow_ai_grouping_article_story")]
        latest = [("news", "0018_expand_categories_and_sources")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(previous)
            apps = executor.loader.project_state(previous).apps
            source = apps.get_model("news", "Source").objects.create(name="Fuente migración importancia")
            feed = apps.get_model("news", "Feed").objects.create(source=source, name="RSS", url="https://example.com/migration-rss")
            story = apps.get_model("news", "Story").objects.create()
            article = apps.get_model("news", "Article").objects.create(
                title="Titular previo sintético", feed=feed, story=story, original_url="https://example.com/migration-importance",
            )
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            updated = apps.get_model("news", "Article").objects.get(pk=article.pk)
            self.assertEqual(updated.story_id, story.pk)
            self.assertEqual(updated.byline, "")
            self.assertIsNone(apps.get_model("news", "Story").objects.get(pk=story.pk).importance_score)
            apps.get_model("news", "Story").objects.filter(pk=story.pk).update(importance_score=5)
            executor = MigrationExecutor(connection)
            executor.migrate(previous)
            apps = executor.loader.project_state(previous).apps
            restored = apps.get_model("news", "Article").objects.get(pk=article.pk)
            self.assertEqual(restored.title, "Titular previo sintético")
            self.assertEqual(restored.story_id, story.pk)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
