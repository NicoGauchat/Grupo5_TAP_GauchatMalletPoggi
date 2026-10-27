from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .ingestion import ELDIARIO_DESCRIPTION_FEED, ELDIARIO_LICENSE, IngestionError, ingest_feed, permitted_summary
from .models import Article, Feed


class ReviewedExcerptTests(SimpleTestCase):
    def setUp(self):
        self.feed = SimpleNamespace(show_summary=True, url=ELDIARIO_DESCRIPTION_FEED,
                                    source=SimpleNamespace(name="elDiario.es", license_url=ELDIARIO_LICENSE))

    def test_only_first_nonempty_short_paragraph_is_kept_from_licensed_rss(self):
        entry = {"author": "Autora de prueba", "summary":
                 '<p><img src="https://example.com/photo"></p><p>Una entradilla &amp; sus detalles.</p><p>' + "Resto " * 400 + "</p>"}
        self.assertEqual(permitted_summary(entry, self.feed), "Una entradilla & sus detalles.")
        entry["summary"] = "<p>" + "x" * 601 + "</p><p>Otro párrafo.</p>"
        self.assertEqual(permitted_summary(entry, self.feed), "")
        self.feed.url = "https://example.com/other-rss"
        self.assertEqual(permitted_summary(entry, self.feed), "")

    def test_missing_attribution_or_identified_third_party_is_excluded(self):
        cases = [{}, {"author": "Reuters"}, {"author": "Autora", "rights": "The Guardian"},
                 {"author": "Autora", "summary": "<p>Texto atribuido a EFE.</p>"}]
        for changes in cases:
            entry = {"summary": "<p>Entradilla de prueba.</p>", **changes}
            with self.subTest(changes=changes):
                self.assertEqual(permitted_summary(entry, self.feed), "")
        self.feed.source.license_url = ""
        self.assertEqual(permitted_summary({"author": "Autora", "summary": "Entradilla."}, self.feed), "")


class ReviewedDescriptionRefreshTests(TestCase):
    def setUp(self):
        self.feed = Feed.objects.select_related("source").get(url=ELDIARIO_DESCRIPTION_FEED)
        self.feed.is_active = True
        self.feed.show_summary = self.feed.allow_ai_briefing = False
        self.feed.save()
        self.entry = {"id": "description-test", "title": "Un anuncio internacional ficticio",
                      "link": "https://example.com/reviewed-article", "author": "Autora de prueba",
                      "published_parsed": timezone.now().utctimetuple(),
                      "summary": "<p>La entradilla detalla un acuerdo ficticio.</p><p>" + "Cuerpo no guardado. " * 200 + "</p>"}

    def download(self):
        return patch("news.ingestion.download_feed", return_value=([self.entry], "", ""))

    def test_explicit_activation_only_changes_reviewed_feed_and_populates_existing_news(self):
        with self.download():
            ingest_feed(self.feed)
        article = Article.objects.get(original_url=self.entry["link"])
        self.assertEqual(article.summary, "")
        other_flags = list(Feed.objects.exclude(pk=self.feed.pk).values_list("pk", "show_summary", "allow_ai_briefing"))
        output = StringIO()
        with self.download() as download:
            call_command("refresh_briefing_descriptions", enable_reviewed=True, stdout=output)
        self.feed.refresh_from_db()
        article.refresh_from_db()
        self.assertTrue(self.feed.show_summary and self.feed.allow_ai_briefing)
        self.assertEqual(article.summary, "La entradilla detalla un acuerdo ficticio.")
        self.assertEqual(article.byline, "Autora de prueba")
        self.assertEqual(Article.objects.filter(original_url=self.entry["link"]).count(), 1)
        self.assertEqual(list(Feed.objects.exclude(pk=self.feed.pk).values_list("pk", "show_summary", "allow_ai_briefing")), other_flags)
        self.assertTrue(download.call_args.kwargs["force_download"])
        self.assertIn("1 entradillas disponibles", output.getvalue())

    def test_default_command_does_not_enable_permissions_or_reactivate_a_paused_feed(self):
        with self.assertRaises(CommandError):
            call_command("refresh_briefing_descriptions", stdout=StringIO())
        self.feed.is_active = False
        self.feed.save()
        with self.assertRaises(CommandError):
            call_command("refresh_briefing_descriptions", enable_reviewed=True, stdout=StringIO())
        self.feed.refresh_from_db()
        self.assertFalse(self.feed.is_active or self.feed.show_summary or self.feed.allow_ai_briefing)

    def test_revocation_clears_stored_description_and_another_feed_cannot_replace_it(self):
        self.feed.show_summary = True
        self.feed.save()
        with self.download():
            ingest_feed(self.feed)
        article = Article.objects.get(original_url=self.entry["link"])
        other = Feed.objects.create(source=self.feed.source, name="Otro canal", url="https://example.com/other-feed", show_summary=True)
        with patch("news.ingestion.download_feed", return_value=([dict(self.entry, summary="No reemplazar")], "", "")):
            ingest_feed(other)
        article.refresh_from_db()
        self.assertEqual(article.summary, "La entradilla detalla un acuerdo ficticio.")
        self.feed.show_summary = False
        self.feed.save()
        with self.download():
            ingest_feed(self.feed)
        article.refresh_from_db()
        self.assertEqual(article.summary, "")

    def test_refresh_failure_is_not_reported_as_success(self):
        with patch("news.ingestion.download_feed", side_effect=IngestionError("HTTP 503")), self.assertRaises(CommandError):
            call_command("refresh_briefing_descriptions", enable_reviewed=True, stdout=StringIO())
