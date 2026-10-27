import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase
from django.utils import timezone

from news.models import Article, ArticleOrigin, Category, Feed, SavedArticle, Source, Story


class PurgeGroupingBacklogTests(TransactionTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.cutoff = self.now - timedelta(hours=48)
        source = Source.objects.create(name="Fuente ficticia", website_url="https://example.test")
        self.feed = Feed.objects.create(source=source, name="Prueba", url="https://example.test/rss",
                                       is_active=True, allow_ai_grouping=True)
        self.old = self.article(72)
        self.protected = [self.article(24), self.article(48), self.article(14 * 24 + 1),
                          self.article(None), self.article(-1),
                          self.article(72, story=Story.objects.create())]
        inactive = Feed.objects.create(source=source, name="Inactivo", url="https://example.test/inactive",
                                       allow_ai_grouping=True)
        denied = Feed.objects.create(source=source, name="Sin permiso", url="https://example.test/denied",
                                     is_active=True)
        self.protected += [self.article(72, feed=inactive), self.article(72, feed=denied)]
        self.user = get_user_model().objects.create_user(username="ficticio")
        SavedArticle.objects.create(user=self.user, article=self.old)
        ArticleOrigin.objects.create(article=self.old, feed=self.feed, guid="ficticio")
        category = Category.objects.create(name="Ficticia", slug="ficticia")
        self.old.categories.add(category)
        self.old.llm_categories.add(category)

    def article(self, hours, **kwargs):
        return Article.objects.create(
            title="Titular ficticio", original_url=f"https://example.test/{Article.objects.count()}",
            published_at=self.now - timedelta(hours=hours) if hours is not None else None,
            **{"feed": self.feed, **kwargs})

    def run_command(self, **kwargs):
        output = StringIO()
        with patch("news.management.commands.purge_grouping_backlog.timezone.now", return_value=self.now):
            call_command("purge_grouping_backlog", published_before=self.cutoff.isoformat(), stdout=output, **kwargs)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_preview_preserves_all_rows(self):
        before = list(Article.objects.order_by("pk").values())
        result = self.run_command()
        self.assertEqual(result[0]["articles"], 1)
        self.assertEqual(result[0]["saved_links"], 1)
        self.assertEqual(before, list(Article.objects.order_by("pk").values()))
        self.assertEqual(SavedArticle.objects.count(), 1)

    def test_apply_deletes_only_target_and_related_rows(self):
        result = self.run_command(apply=True, expected_count=1)
        self.assertEqual(result[1]["deleted_articles"], 1)
        self.assertFalse(Article.objects.filter(pk=self.old.pk).exists())
        self.assertEqual(Article.objects.count(), len(self.protected))
        self.assertEqual(ArticleOrigin.objects.count(), 0)
        self.assertEqual(SavedArticle.objects.count(), 0)
        self.assertTrue(Category.objects.filter(slug="ficticia").exists())
        self.assertEqual(Story.objects.count(), 1)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_mismatched_or_missing_count_does_not_delete(self):
        for kwargs in ({"apply": True}, {"apply": True, "expected_count": 2},
                       {"apply": True, "expected_count": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(CommandError):
                self.run_command(**kwargs)
            self.assertTrue(Article.objects.filter(pk=self.old.pk).exists())

    def test_invalid_or_recent_cutoff_does_not_delete(self):
        for cutoff in ("invalid", "2026-99-99T00:00:00Z", self.cutoff.replace(tzinfo=None).isoformat(),
                       (self.now - timedelta(hours=24)).isoformat()):
            with self.subTest(cutoff=cutoff), self.assertRaises(CommandError):
                call_command("purge_grouping_backlog", published_before=cutoff,
                             apply=True, expected_count=1, stdout=StringIO())
        self.assertTrue(Article.objects.filter(pk=self.old.pk).exists())

    def test_legacy_group_is_pending_but_group_is_preserved(self):
        legacy = Story.objects.create(grouping_version=0)
        self.old.story = legacy
        self.old.save(update_fields=["story"])
        self.run_command(apply=True, expected_count=1)
        self.assertFalse(Article.objects.filter(pk=self.old.pk).exists())
        self.assertTrue(Story.objects.filter(pk=legacy.pk).exists())
