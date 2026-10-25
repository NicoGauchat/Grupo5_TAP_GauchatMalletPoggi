import json
from importlib import import_module
from datetime import timedelta
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .llm_grouping import GroupingError, group_articles, validate_groups
from .models import Article, Category, Feed, SavedArticle, Source, Story, UserPreference


class GroupingValidationTests(SimpleTestCase):
    def test_accepts_complete_partition_and_rejects_invalid_references(self):
        valid = {"groups": [{"story_id": 7, "article_ids": [1, 2]}, {"story_id": 0, "article_ids": [3]}]}
        self.assertEqual(validate_groups(valid, {1, 2, 3}, {7}), valid["groups"])
        for groups in (
            [], [{"story_id": 0, "article_ids": [1]}],
            [{"story_id": 0, "article_ids": [1, 2, 3, 4]}],
            [{"story_id": 8, "article_ids": [1, 2, 3]}],
            [{"story_id": True, "article_ids": [1, 2, 3]}],
            [{"story_id": 0, "article_ids": [True, 2, 3]}],
            [{"story_id": 0, "article_ids": [1, 1, 2, 3]}],
            [{"story_id": 7, "article_ids": [1]}, {"story_id": 7, "article_ids": [2, 3]}],
            [{"story_id": 0, "article_ids": [1, 2]}, {"story_id": 0, "article_ids": [2, 3]}],
        ):
            with self.subTest(groups=groups), self.assertRaises(GroupingError):
                validate_groups({"groups": groups}, {1, 2, 3}, {7})


class StoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="lector-acontecimientos")
        cls.category = Category.objects.get(slug="tecnologia")
        UserPreference.objects.create(user=cls.user).categories.add(cls.category)
        cls.feeds = [Feed.objects.create(
            source=Source.objects.create(name=f"Medio {index}"), name="RSS",
            url=f"https://example.com/{index}/rss", is_active=True, allow_ai_grouping=True,
        ) for index in range(3)]

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("category_news", args=[self.category.slug])

    def article(self, title, index=0, story=None, age=1):
        article = Article.objects.create(
            title=title, feed=self.feeds[index], story=story, language="es",
            original_url=f"https://example.com/article/{Article.objects.count()}",
            published_at=timezone.now() - timedelta(hours=age), summary="contenido que no debe enviarse",
        )
        article.categories.add(self.category)
        return article

    def test_single_card_lists_all_sources_and_respects_filters_and_permissions(self):
        story = Story.objects.create()
        older = self.article("Primer titular", story=story, age=3)
        latest = self.article("Segunda cobertura", index=1, story=story)
        latest.categories.clear()
        latest.llm_categories.add(self.category)
        pending = self.article("Noticia todavía sin agrupar", index=2)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["articles"]), 2)
        self.assertEqual(response.context["article_count"], 2)
        self.assertContains(response, f'id="story-{story.pk}"', count=1)
        self.assertContains(response, "Ver 2 fuentes · 2 coberturas")
        for article in (older, latest, pending):
            self.assertContains(response, article.original_url)
        self.assertContains(response, "Titular de Medio 1")
        filtered = self.client.get(self.url, {"source": self.feeds[0].source_id})
        self.assertEqual([a.pk for a in filtered.context["articles"]], [older.pk])
        self.assertContains(filtered, latest.original_url)
        preference = UserPreference.objects.get(user=self.user)
        preference.classification_mode = "rules"
        preference.save()
        self.assertEqual(self.client.get(self.url).context["article_count"], 2)
        self.assertEqual(self.client.get(reverse("news_feed")).context["sections"][0]["article_count"], 2)
        self.feeds[1].allow_ai_grouping = False
        self.feeds[1].save()
        self.assertNotContains(self.client.get(self.url, {"source": self.feeds[0].source_id}), latest.original_url)

    def test_same_medium_counts_once_and_expired_inactive_coverages_are_hidden(self):
        story = Story.objects.create()
        self.article("Primera cobertura", story=story)
        self.article("Ampliación", story=story)
        expired = self.article("Vencida", index=1, story=story, age=15 * 24)
        inactive = self.article("Inactiva", index=2, story=story)
        self.feeds[2].is_active = False
        self.feeds[2].save()
        response = self.client.get(self.url)
        self.assertContains(response, "Ver 1 fuente · 2 coberturas")
        self.assertNotContains(response, expired.original_url)
        self.assertNotContains(response, inactive.original_url)

    def test_grouped_pagination_uses_unique_stories_and_keeps_bookmarks(self):
        for index in range(21):
            story = Story.objects.create()
            self.article(f"Cobertura {index} A", story=story)
            self.article(f"Cobertura {index} B", index=1, story=story)
        first = self.client.get(self.url)
        rows = first.context["articles"]
        self.assertEqual(len(rows), 10)
        self.assertEqual(first.context["article_count"], 21)
        saved = rows[0]
        self.client.post(reverse("save_article", args=[saved.pk]))
        self.assertTrue(SavedArticle.objects.filter(user=self.user, article=saved).exists())
        second = self.client.get(first.context["next_url"], HTTP_ACCEPT="application/json").json()
        self.assertEqual(second["html"].count('data-article-id='), 9)
        for article in rows:
            self.assertNotIn(f'id="story-{article.story_id}"', second["html"])
        last = self.client.get(second["next_url"], HTTP_ACCEPT="application/json").json()
        self.assertEqual(last["html"].count('data-article-id='), 2)
        self.assertIsNone(last["next_url"])

    def test_command_is_incremental_idempotent_and_does_not_send_content(self):
        first = self.article("El gobierno anuncia una medida")
        second = self.article("Anunciaron una medida", index=1)
        def group(batch, candidates):
            return [{"story_id": candidates[0].story_id if candidates else 0,
                     "article_ids": [article.pk for article in batch]}]
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=group) as model:
            call_command("group_news_ai", stdout=StringIO())
            first.refresh_from_db()
            second.refresh_from_db()
            self.assertEqual(first.story_id, second.story_id)
            call_command("group_news_ai", stdout=StringIO())
            self.assertEqual(model.call_count, 1)
            third = self.article("Otro medio informa la medida", index=2)
            call_command("group_news_ai", stdout=StringIO())
            third.refresh_from_db()
            self.assertEqual(third.story_id, first.story_id)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"}):
            with patch("news.llm_grouping.genai.Client") as client:
                generate = client.return_value.__enter__.return_value.models.generate_content
                generate.return_value.text = json.dumps({"groups": [{"story_id": 0, "article_ids": [first.pk]}]})
                group_articles([first], [])
                self.assertNotIn(first.summary, generate.call_args.kwargs["contents"])
                self.assertEqual(client.call_args.kwargs["http_options"].timeout, 60_000)

    def test_failure_limit_and_permission_keep_articles_visible_and_pending(self):
        pending = self.article("Pendiente")
        forbidden = self.article("Sin permiso", index=1)
        self.feeds[1].allow_ai_grouping = False
        self.feeds[1].save()
        self.article("Antigua", age=15 * 24)
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=GroupingError("Error")) as model:
            with self.assertRaises(CommandError):
                call_command("group_news_ai", stdout=StringIO())
            self.assertEqual([article.pk for article in model.call_args.args[0]], [pending.pk])
        self.assertEqual(Story.objects.count(), 0)
        self.assertEqual(self.client.get(self.url).context["article_count"], 2)
        with patch("news.management.commands.group_news_ai.group_articles") as model:
            with self.assertRaises(CommandError):
                call_command("group_news_ai", limit=0)
            model.assert_not_called()
        forbidden.refresh_from_db()
        self.assertIsNone(forbidden.story_id)

    def test_candidate_chunks_find_older_group_and_invalidate_importance(self):
        old_story = Story.objects.create(importance_score=4, importance_scored_at=timezone.now())
        self.article("Cobertura de ayer", story=old_story, age=4)
        self.article("Otro acontecimiento", story=Story.objects.create(), age=2)
        pending = self.article("Nueva cobertura de ayer")
        def group(batch, candidates):
            matched = next((article.story_id for article in candidates if article.story_id == old_story.pk), 0)
            return [{"story_id": matched, "article_ids": [article.pk for article in batch]}]
        with patch("news.management.commands.group_news_ai.MAX_CANDIDATES", 1), patch(
            "news.management.commands.group_news_ai.group_articles", side_effect=group,
        ) as model:
            call_command("group_news_ai", stdout=StringIO())
            self.assertEqual(model.call_count, 2)
        pending.refresh_from_db()
        old_story.refresh_from_db()
        self.assertEqual(pending.story_id, old_story.pk)
        self.assertIsNone(old_story.importance_scored_at)
        self.assertEqual(old_story.importance_score, 4)

    def test_cleanup_drops_empty_stories_without_extending_saved_articles(self):
        story = Story.objects.create()
        article = self.article("Vieja", story=story, age=15 * 24)
        SavedArticle.objects.create(user=self.user, article=article)
        call_command("purge_old_articles", dry_run=True, stdout=StringIO())
        self.assertTrue(Story.objects.filter(pk=story.pk).exists())
        call_command("purge_old_articles", stdout=StringIO())
        self.assertFalse(Story.objects.filter(pk=story.pk).exists())
        self.assertFalse(SavedArticle.objects.filter(article_id=article.pk).exists())

    @skipUnless(connection.vendor == "postgresql", "Stemming requiere PostgreSQL")
    def test_search_chooses_best_matching_coverage_then_keeps_other_sources(self):
        story = Story.objects.create()
        match = self.article("Empresas investigan robots", story=story, age=2)
        other = self.article("Anuncio del laboratorio", index=1, story=story)
        response = self.client.get(self.url, {"q": "empresa robots"})
        self.assertEqual([article.pk for article in response.context["articles"]], [match.pk])
        self.assertContains(response, other.original_url)


class StoryMigrationTests(TransactionTestCase):
    def test_existing_articles_survive_forward_and_reverse(self):
        previous = [("news", "0015_educational_feeds_and_briefing_status")]
        target = [("news", "0016_story_feed_allow_ai_grouping_article_story")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(previous)
            old = executor.loader.project_state(previous).apps
            source = old.get_model("news", "Source").objects.create(name="Medio migración sintético")
            urls = import_module("news.migrations.0015_educational_feeds_and_briefing_status").FEEDS
            for url in urls:
                old.get_model("news", "Feed").objects.get_or_create(url=url, defaults={"source_id": source.pk, "name": "RSS"})
            feed = old.get_model("news", "Feed").objects.get(url=urls[0])
            article = old.get_model("news", "Article").objects.create(
                feed_id=feed.pk, title="Titular previo", original_url="https://example.com/previo",
            )
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            FeedModel = current.get_model("news", "Feed")
            self.assertEqual(FeedModel.objects.filter(allow_ai_grouping=True).count(), 11)
            self.assertIsNone(current.get_model("news", "Article").objects.get(pk=article.pk).story_id)
            self.assertFalse(FeedModel.objects.create(source_id=feed.source_id, name="Nuevo", url="https://example.com/new").allow_ai_grouping)
            story = current.get_model("news", "Story").objects.create()
            current.get_model("news", "Article").objects.filter(pk=article.pk).update(story=story)
            executor = MigrationExecutor(connection)
            executor.migrate(previous)
            restored = executor.loader.project_state(previous).apps
            self.assertEqual(restored.get_model("news", "Article").objects.get(pk=article.pk).title, "Titular previo")
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
