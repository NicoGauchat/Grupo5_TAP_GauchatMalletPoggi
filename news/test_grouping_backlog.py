import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from news.models import GROUPING_VERSION, Article, Feed, Source, Story


class GroupingBacklogTests(TransactionTestCase):
    def test_age_boundaries_eligibility_and_read_only_counts(self):
        now = timezone.now()
        source = Source.objects.create(name="Fuente ficticia", website_url="https://example.test")
        feed = Feed.objects.create(source=source, name="Prueba", url="https://example.test/rss",
                                   is_active=True, allow_ai_grouping=True)
        inactive = Feed.objects.create(source=source, name="Inactivo", url="https://example.test/inactive",
                                       allow_ai_grouping=True)
        denied = Feed.objects.create(source=source, name="Sin permiso", url="https://example.test/denied",
                                     is_active=True)
        legacy = Story.objects.create(grouping_version=0)
        verified = Story.objects.create(grouping_version=GROUPING_VERSION)
        for index, (hours, selected_feed, story) in enumerate([
            (0, feed, None), (24, feed, None), (24.1, feed, None), (48, feed, None),
            (48.1, feed, None), (14 * 24, feed, legacy), (14 * 24 + 1, feed, None),
            (-1, feed, None), (None, feed, None), (1, inactive, None), (1, denied, None),
            (1, feed, verified),
        ]):
            Article.objects.create(feed=selected_feed, story=story, title="Titular ficticio",
                                   original_url=f"https://example.test/{index}",
                                   published_at=now - timedelta(hours=hours) if hours is not None else None)
        before = list(Article.objects.order_by("pk").values())
        output = StringIO()
        with patch("news.management.commands.report_grouping_backlog.timezone.now", return_value=now):
            call_command("report_grouping_backlog", stdout=output)
        result = json.loads(output.getvalue())
        self.assertEqual([result[key] for key in ("total", "up_to_24h", "over_24h_up_to_48h", "over_48h", "legacy_groups")],
                         [6, 2, 2, 2, 1])
        self.assertEqual(result["oldest"], str(now - timedelta(days=14)))
        self.assertEqual(before, list(Article.objects.order_by("pk").values()))

    def test_empty_backlog(self):
        output = StringIO()
        call_command("report_grouping_backlog", stdout=output)
        result = json.loads(output.getvalue())
        self.assertEqual(result["total"], 0)
        self.assertIsNone(result["oldest"])
        self.assertIsNone(result["newest"])
