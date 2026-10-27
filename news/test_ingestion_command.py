from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .ingestion import IngestionError, IngestionResult
from .models import Feed, Source


class IngestionCommandTests(TestCase):
    def setUp(self):
        Feed.objects.update(is_active=False)
        source = Source.objects.create(name="Fuente sintética")
        for index in range(3):
            Feed.objects.create(source=source, name=str(index), url=f"https://example.com/rss/{index}", is_active=True)

    def run_command(self):
        return call_command("ingest_feeds", stdout=StringIO(), stderr=StringIO())

    @patch("news.management.commands.ingest_feeds.ingest_feed")
    def test_partial_failure_attempts_remaining_feeds_and_reports_distinct_exit(self, ingest):
        ingest.side_effect = [IngestionError("HTTP 404"), IngestionResult(created=2), IngestionResult(unchanged=True)]
        with self.assertRaises(CommandError) as caught:
            self.run_command()
        self.assertEqual(caught.exception.returncode, 2)
        self.assertIn("2 consultados correctamente", str(caught.exception))
        self.assertEqual(ingest.call_count, 3)

    @patch("news.management.commands.ingest_feeds.ingest_feed", side_effect=IngestionError("HTTP 503"))
    def test_total_failure_is_not_partial(self, ingest):
        with self.assertRaises(CommandError) as caught:
            self.run_command()
        self.assertEqual(caught.exception.returncode, 1)
        self.assertEqual(ingest.call_count, 3)

    @patch("news.management.commands.ingest_feeds.ingest_feed")
    def test_unexpected_failure_is_not_marked_partial(self, ingest):
        ingest.side_effect = [IngestionResult(created=1), RuntimeError("fallo interno")]
        with self.assertRaises(RuntimeError):
            self.run_command()
        self.assertEqual(ingest.call_count, 2)

    @patch("news.management.commands.ingest_feeds.ingest_feed", return_value=IngestionResult(unchanged=True))
    def test_all_feeds_successful_returns_normally(self, ingest):
        self.run_command()
        self.assertEqual(ingest.call_count, 3)
