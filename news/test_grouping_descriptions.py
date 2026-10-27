import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from news.ingestion import ELDIARIO_DESCRIPTION_FEED, ELDIARIO_LICENSE
from news.llm_grouping import group_articles, metadata


class GroupingDescriptionTests(SimpleTestCase):
    def article(self, pk=1, **changes):
        source = SimpleNamespace(name="Fuente ficticia", license_url="")
        feed = SimpleNamespace(source=source, url="https://example.test/rss", is_active=True,
                               allow_ai_grouping=True, show_summary=True, allow_ai_briefing=False)
        return SimpleNamespace(**{"pk": pk, "story_id": 7, "title": "Titular ficticio",
                                  "published_at": timezone.now(), "language": "es", "feed": feed,
                                  "summary": "<p>El acuerdo &amp; sus detalles.</p>", "byline": "Autora ficticia",
                                  **changes})

    def test_description_is_clean_and_independent_of_briefing_permission(self):
        payload = metadata(self.article())
        self.assertEqual(payload["rss_description"], "El acuerdo & sus detalles.")
        self.assertNotIn("byline", payload)
        self.assertNotIn("url", payload)

    def test_disabled_permissions_or_inactive_feed_omit_description(self):
        for field in ("show_summary", "allow_ai_grouping", "is_active"):
            article = self.article()
            setattr(article.feed, field, False)
            with self.subTest(field=field):
                self.assertNotIn("rss_description", metadata(article))

    def test_empty_and_full_article_fields_are_not_sent_or_truncated(self):
        for value in ("", "  <p></p>  ", "x" * 601):
            with self.subTest(value_length=len(value)):
                self.assertNotIn("rss_description", metadata(self.article(summary=value)))
        self.assertEqual(len(metadata(self.article(summary="x" * 600))["rss_description"]), 600)

    def test_reviewed_eldiario_requires_license_author_and_excludes_third_parties(self):
        article = self.article()
        article.feed.url = ELDIARIO_DESCRIPTION_FEED
        article.feed.source.name = "elDiario.es"
        article.feed.source.license_url = ELDIARIO_LICENSE
        self.assertIn("rss_description", metadata(article))
        article.byline = "Reuters"
        self.assertNotIn("rss_description", metadata(article))
        article.byline = ""
        self.assertNotIn("rss_description", metadata(article))
        article.byline = "Autora ficticia"
        article.feed.source.license_url = ""
        self.assertNotIn("rss_description", metadata(article))

    def test_proposal_and_audit_receive_descriptions_for_new_article_and_anchor(self):
        article = self.article(summary="La cobertura nueva identifica un acuerdo ficticio.")
        anchor = self.article(pk=9, summary="La referencia identifica el mismo acuerdo ficticio.")
        for provider in ("gemini", "groq"):
            replies = [{"groups": [{"story_id": 7, "article_ids": [1]}]},
                       {"decisions": [{"article_id": 1, "same_event": True, "reason": "Mismo acuerdo."}]}]
            with self.subTest(provider=provider), patch("news.llm_grouping.api_key_for", return_value="ficticia"), patch(
                "news.llm_grouping.request_groups", side_effect=replies,
            ) as request:
                groups = group_articles([article], [anchor], provider=provider)
                self.assertEqual(groups, [{"story_id": 7, "article_ids": [1]}])
                proposal, audit = [json.loads(call.args[0].split("\n", 1)[1]) for call in request.call_args_list]
                self.assertEqual(proposal["new_articles"][0]["rss_description"], article.summary)
                self.assertEqual(proposal["existing_stories"][0]["rss_description"], anchor.summary)
                self.assertEqual(audit["pairs"][0]["candidate"]["rss_description"], article.summary)
                self.assertEqual(audit["pairs"][0]["anchor"]["rss_description"], anchor.summary)

    def test_no_description_still_allows_grouping_and_negative_audit_separates(self):
        for description, accepted in (("", True), ("Otro episodio ficticio.", False)):
            article = self.article(summary=description)
            replies = [{"groups": [{"story_id": 7, "article_ids": [1]}]},
                       {"decisions": [{"article_id": 1, "same_event": accepted, "reason": "Decisión ficticia."}]}]
            with self.subTest(description=description), patch("news.llm_grouping.api_key_for", return_value="ficticia"), patch(
                "news.llm_grouping.request_groups", side_effect=replies,
            ):
                self.assertEqual(group_articles([article], [self.article(pk=9)]),
                                 [{"story_id": 7 if accepted else 0, "article_ids": [1]}])
