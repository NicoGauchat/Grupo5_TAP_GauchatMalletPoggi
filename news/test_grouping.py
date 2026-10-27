import json
from importlib import import_module
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
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

from .llm_grouping import GroupingError, decode_assignments, group_articles, request_groups, validate_confirmations, validate_groups
from .models import Article, Category, Feed, SavedArticle, Source, Story, UserPreference
from .llm_transport import BackupError, ModelList
from .management.commands.group_news_ai import Command as GroupNewsCommand


class GroupingValidationTests(SimpleTestCase):
    def test_closed_audit_map_preserves_negative_decisions_and_requires_all_fields(self):
        schema = {"properties": {"decisions": {"type": "object", "required": ["2"]}}}
        result = decode_assignments({"decisions": {"2": {"same_event": False, "reason": "Hechos distintos."}}}, schema)
        self.assertEqual(validate_confirmations(result, {2}), set())
        for result, reason in [({"decisions": {}}, "confirmation_keys"),
                               ({"decisions": {"2": {"same_event": False}}}, "confirmation_fields")]:
            with self.subTest(reason=reason), self.assertRaisesRegex(GroupingError, f"reason={reason}"):
                decode_assignments(result, schema)

    def test_assignment_object_coalesces_groups_and_rejects_missing_unknown_or_conflicting_anchors(self):
        schema = {"properties": {"groups": {"type": "object", "required": ["1", "2", "3"]}},
                  "$defs": {"target": {"enum": ["new:1", "new:2", "new:3", "story:7"]}}}
        result = decode_assignments({"groups": {"1": "story:7", "2": "story:7", "3": "new:3"}}, schema)
        self.assertEqual(validate_groups(result, {1, 2, 3}, {7}), [
            {"story_id": 7, "article_ids": [1, 2]}, {"story_id": 0, "article_ids": [3]}])
        cases = [({"1": "new:1"}, "assignment_keys"),
                 ({"1": "new:1", "2": "new:2", "3": "new:3", "999": "new:1"}, "assignment_keys"),
                 ({"1": "story:999", "2": "new:2", "3": "new:3"}, "assignment_target"),
                 ({"1": "new:2", "2": "story:7", "3": "new:3"}, "assignment_anchor"),
                 ({"1": "new:2", "2": "new:1", "3": "new:3"}, "assignment_anchor")]
        for assignments, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(GroupingError, f"reason={reason}"):
                decode_assignments({"groups": assignments}, schema)

    def test_oversized_backup_request_signals_smaller_candidate_blocks(self):
        with patch("news.llm_grouping.request_backup", side_effect=BackupError("request_too_large")):
            with self.assertRaises(GroupingError) as caught:
                request_groups("synthetic", {}, "primary-test", provider="groq")
        self.assertTrue(caught.exception.reduce_candidates)
        self.assertFalse(caught.exception.retryable)

    def test_oversized_later_block_restarts_whole_batch_without_losing_candidates(self):
        batch = [SimpleNamespace(pk=1), SimpleNamespace(pk=2)]
        candidates = [SimpleNamespace(story_id=pk) for pk in (11, 12, 13)]
        replies = [
            [{"story_id": 11, "article_ids": [1]}, {"story_id": 0, "article_ids": [2]}],
            GroupingError("too large", retryable=False, reduce_candidates=True),
            [{"story_id": 0, "article_ids": [1, 2]}],
            [{"story_id": 12, "article_ids": [1]}, {"story_id": 0, "article_ids": [2]}],
            [{"story_id": 0, "article_ids": [2]}],
        ]
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=replies) as model:
            groups, limit = GroupNewsCommand(stderr=StringIO()).propose_batch(batch, candidates, 2)
        self.assertEqual(limit, 1)
        self.assertEqual([(row["story_id"], row["article_ids"]) for row in groups], [(12, [1]), (0, [2])])
        self.assertEqual([article.pk for article in model.call_args_list[2].args[0]], [1, 2])
        self.assertEqual([call.args[1][0].story_id for call in model.call_args_list[2:]], [11, 12, 13])

    def test_reduction_stops_at_one_candidate_and_does_not_retry_other_errors(self):
        candidates = [SimpleNamespace(story_id=pk) for pk in (11, 12)]
        for shrink, expected_calls in ((True, 2), (False, 1)):
            with self.subTest(shrink=shrink), patch("news.management.commands.group_news_ai.group_articles",
                side_effect=GroupingError("failed", retryable=False, reduce_candidates=shrink)) as model:
                with self.assertRaises(GroupingError):
                    GroupNewsCommand(stderr=StringIO()).propose_batch([SimpleNamespace(pk=1)], candidates, 2)
                self.assertEqual(model.call_count, expected_calls)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"})
    def test_schema_limits_proposal_and_audit_to_received_numeric_references(self):
        source = SimpleNamespace(source=SimpleNamespace(name="Fuente ficticia"))
        articles = [SimpleNamespace(pk=pk, title="Cobertura ficticia", language="es",
                                    published_at=timezone.now(), feed=source) for pk in (101, 102)]
        anchor = SimpleNamespace(pk=9, story_id=7, title="Hecho ficticio", language="es",
                                 published_at=timezone.now(), feed=source)
        groups = {"groups": [{"story_id": 7, "article_ids": [101, 102]}]}
        audit = {"decisions": {str(pk): {"same_event": True, "reason": "Mismo hecho ficticio."}
                               for pk in (101, 102)}}
        with patch("news.llm_grouping.genai.Client") as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.side_effect = [SimpleNamespace(text=json.dumps({"groups": {"101": "story:7", "102": "story:7"}})),
                                    SimpleNamespace(text=json.dumps(audit))]
            self.assertEqual(group_articles(articles, [anchor]), groups["groups"])
            proposal_config = generate.call_args_list[0].kwargs["config"]
            proposal = proposal_config.response_json_schema
            assignments = proposal["properties"]["groups"]
            self.assertEqual(set(assignments["required"]), {"101", "102"})
            self.assertFalse(assignments["additionalProperties"])
            self.assertEqual(proposal["$defs"]["target"]["enum"], ["new:101", "new:102", "story:7"])
            self.assertEqual(assignments["properties"]["101"]["$ref"], "#/$defs/target")
            self.assertIsNone(proposal_config.response_schema)
            audit_schema = generate.call_args_list[1].kwargs["config"].response_json_schema
            self.assertEqual(audit_schema["properties"]["decisions"]["required"], ["101", "102"])
            self.assertFalse(audit_schema["properties"]["decisions"]["additionalProperties"])
            self.assertEqual(audit_schema["$defs"]["decision"]["properties"]["same_event"], {"type": "boolean"})

    @patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"})
    def test_schema_restriction_does_not_replace_local_validation(self):
        article = SimpleNamespace(pk=1, title="Titular ficticio", language="es", published_at=timezone.now(),
                                  feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")))
        with patch("news.llm_grouping.genai.Client") as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.return_value.text = json.dumps({"groups": {"999": "new:999"}})
            with self.assertRaisesRegex(GroupingError, "reason=assignment_keys"):
                group_articles([article], [])
            self.assertEqual(generate.call_count, 3)

    def test_reference_diagnostics_explain_failure_without_echoing_ids(self):
        cases = [
            ([{"story_id": 9876543, "article_ids": [1]}], "unknown_story_id"),
            ([{"story_id": 7, "article_ids": [1]}, {"story_id": 7, "article_ids": [2]}], "repeated_story_id"),
            ([{"story_id": 0, "article_ids": []}], "empty_article_ids"),
            ([{"story_id": 0, "article_ids": [9876543]}], "unknown_article_id"),
            ([{"story_id": 0, "article_ids": [1, 1]}], "repeated_article_id"),
        ]
        for rows, reason in cases:
            with self.subTest(reason=reason), self.assertRaises(GroupingError) as caught:
                validate_groups({"groups": rows}, {1, 2}, {7})
            self.assertIn(f"reason={reason}", str(caught.exception))
            self.assertNotIn("9876543", str(caught.exception))

    @patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"})
    def test_retries_invalid_response_and_recovers_before_saving(self):
        article = SimpleNamespace(pk=1, title="Titular de ensayo", language="es", published_at=timezone.now(),
                                  feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")))
        valid = {"groups": [{"story_id": 0, "article_ids": [1]}]}
        with patch("news.llm_grouping.request_groups", side_effect=[{"groups": []}, {"groups": []}, valid]) as model:
            self.assertEqual(group_articles([article], []), valid["groups"])
            self.assertEqual(model.call_count, 3)
        with patch("news.llm_grouping.request_groups", return_value={"groups": []}) as model:
            with self.assertRaises(GroupingError):
                group_articles([article], [])
            self.assertEqual(model.call_count, 3)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"})
    def test_transient_failures_retry_three_times_but_quota_and_config_stop(self):
        from google.genai import errors

        article = SimpleNamespace(pk=1, title="Titular", language="es", published_at=timezone.now(),
                                  feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")))
        for status in (503, 504, 429, 403):
            with self.subTest(status=status), patch("news.llm_grouping.genai.Client") as client, patch("news.llm_grouping.time.sleep") as sleep:
                generate = client.return_value.__enter__.return_value.models.generate_content
                generate.side_effect = errors.APIError(status, {"error": {"message": "private-provider-message"}})
                with self.assertRaises(GroupingError) as caught:
                    group_articles([article], [])
                count = 3 if status in (503, 504) else 1
                self.assertEqual(generate.call_count, count)
                self.assertEqual(sleep.call_count, count - 1)
                self.assertNotIn("private-provider-message", str(caught.exception))
                self.assertEqual(client.call_args.kwargs["http_options"].retry_options.attempts, 1)

    def test_quality_command_checks_pairs_without_database_access(self):
        with patch("news.management.commands.check_news_grouping.group_articles") as model:
            model.return_value = [{"story_id": 0, "article_ids": [1, 2]},
                                  {"story_id": 0, "article_ids": [3, 4]},
                                  {"story_id": 0, "article_ids": [5, 6]}]
            call_command("check_news_grouping", stdout=StringIO())
            self.assertEqual(len(model.call_args.args[0]), 6)
            call_command("check_news_grouping", provider="groq", candidates=25, stdout=StringIO())
            self.assertEqual(model.call_args.kwargs["provider"], "groq")
            self.assertEqual(len(model.call_args.args[1]), 25)
            self.assertFalse({a.pk for a in model.call_args.args[0]} & {a.pk for a in model.call_args.args[1]})
            model.return_value[0]["story_id"] = 2000
            with self.assertRaises(CommandError):
                call_command("check_news_grouping", provider="groq", candidates=25, stdout=StringIO())
            model.return_value = [{"story_id": 0, "article_ids": [1, 2, 3, 4, 5, 6]}]
            with self.assertRaises(CommandError):
                call_command("check_news_grouping", stdout=StringIO())

    def test_confirmation_requires_explicit_boolean_and_complete_unique_ids(self):
        valid = {"decisions": [{"article_id": 2, "same_event": True, "reason": "Mismo anuncio."},
                               {"article_id": 3, "same_event": False, "reason": "Otro hecho."}]}
        self.assertEqual(validate_confirmations(valid, {2, 3}), {2})
        for decisions in ([], [valid["decisions"][0]] * 2,
                          [{"article_id": 2, "same_event": 1, "reason": "Mismo hecho."}],
                          [{"article_id": True, "same_event": True, "reason": "Mismo hecho."}],
                          [{"article_id": 2, "same_event": True, "reason": ""}],
                          [{"article_id": 9, "same_event": True, "reason": "Mismo hecho."}]):
            with self.subTest(decisions=decisions), self.assertRaises(GroupingError):
                validate_confirmations({"decisions": decisions}, {2, 3} if len(decisions) == 2 else {2})

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
                generate.return_value.text = json.dumps({"groups": {str(first.pk): f"new:{first.pk}"}})
                group_articles([first], [])
                self.assertNotIn(first.summary, generate.call_args.kwargs["contents"])
                self.assertEqual(client.call_args.kwargs["http_options"].timeout, 60_000)

    def test_command_processes_all_selected_articles_in_small_requests_without_duplicates(self):
        articles = [self.article(f"Titular sintético {index}") for index in range(23)]
        batches = []

        def group(batch, candidates):
            batches.append([article.pk for article in batch])
            return [{"story_id": 0, "article_ids": [article.pk]} for article in batch]

        with patch("news.management.commands.group_news_ai.group_articles", side_effect=group):
            call_command("group_news_ai", stdout=StringIO())
        self.assertTrue(all(len(batch) <= 10 for batch in batches))
        sent = [pk for batch in batches for pk in batch]
        self.assertEqual(len(sent), len(articles))
        self.assertEqual(set(sent), {article.pk for article in articles})
        self.assertEqual(Article.objects.filter(story__isnull=False).count(), 23)

    def test_new_group_records_the_actual_backup_model(self):
        article = self.article("Titular para respaldo")
        with patch("news.management.commands.group_news_ai.group_articles", return_value=ModelList(
            [{"story_id": 0, "article_ids": [article.pk]}], "groq:openai/gpt-oss-20b",
        )):
            call_command("group_news_ai", stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.story.llm_model, "groq:openai/gpt-oss-20b")

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
        self.article("Otro acontecimiento", story=Story.objects.create(), age=2)
        old_story = Story.objects.create(importance_score=4, importance_scored_at=timezone.now())
        self.article("Cobertura de ayer", story=old_story, age=4)
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
        self.assertIsNone(old_story.importance_score)

    def test_second_pass_separates_unrelated_headline_and_accepts_same_event_in_another_language(self):
        first = self.article("Editorial Faro presenta un estudio sobre libros digitales", age=3)
        other = self.article("Banco Delta anuncia su dividendo trimestral", index=1)
        same = self.article("Faro publishes its study of digital books", index=2)
        same.language = "en"
        same.save()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"}), patch("news.llm_grouping.genai.Client") as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.side_effect = [
                type("Response", (), {"text": json.dumps({"groups": {
                    str(pk): f"new:{first.pk}" for pk in (first.pk, other.pk, same.pk)
                }})})(),
                type("Response", (), {"text": json.dumps({"decisions": {
                    str(other.pk): {"same_event": False, "reason": "Es un dividendo, no el estudio."},
                    str(same.pk): {"same_event": True, "reason": "Es la publicación del mismo estudio."},
                }})})(),
            ]
            groups = group_articles([first, other, same], [])
            self.assertEqual(groups, [{"story_id": 0, "article_ids": [first.pk, same.pk]},
                                      {"story_id": 0, "article_ids": [other.pk]}])
            self.assertEqual(generate.call_count, 2)
            payload = json.loads(generate.call_args.kwargs["contents"].split("\n", 1)[1])
            self.assertEqual({pair["anchor"]["article_id"] for pair in payload["pairs"]}, {first.pk})
            self.assertNotIn(first.summary, generate.call_args.kwargs["contents"])

    def test_legacy_group_is_shown_individually_then_reprocessed_without_losing_bookmarks(self):
        legacy = Story.objects.create(grouping_version=0, importance_score=4)
        first = self.article("Estudio editorial", story=legacy, age=2)
        other = self.article("Dividendo de un banco", index=1, story=legacy)
        SavedArticle.objects.create(user=self.user, article=first)
        response = self.client.get(self.url, {"sort": "important"})
        self.assertEqual(response.context["article_count"], 2)
        self.assertNotContains(response, "Ver 2 fuentes")
        self.assertNotContains(response, "Importancia general 4/5")
        for article in (first, other):
            self.assertContains(response, f'id="news-{article.pk}"')
        def split(batch, candidates):
            self.assertEqual(candidates, [])
            return [{"story_id": 0, "article_ids": [article.pk]} for article in batch]
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=split):
            call_command("group_news_ai", stdout=StringIO())
        first.refresh_from_db()
        other.refresh_from_db()
        self.assertNotEqual(first.story_id, other.story_id)
        self.assertTrue(first.has_verified_story)
        self.assertTrue(SavedArticle.objects.filter(user=self.user, article=first).exists())
        self.assertTrue(first.categories.filter(pk=self.category.pk).exists())

    def test_invalid_confirmation_keeps_legacy_links_unchanged_and_hidden(self):
        legacy = Story.objects.create(grouping_version=0)
        first = self.article("Primer acontecimiento", story=legacy)
        other = self.article("Segundo acontecimiento", index=1, story=legacy)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "prueba"}), patch("news.llm_grouping.request_groups") as model:
            model.side_effect = [{"groups": [{"story_id": 0, "article_ids": [first.pk, other.pk]}]},
                                 {"decisions": []}] * 3
            with self.assertRaises(CommandError):
                call_command("group_news_ai", stdout=StringIO())
            self.assertEqual(model.call_count, 6)
        first.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(first.story_id, legacy.pk)
        self.assertEqual(other.story_id, legacy.pk)
        self.assertEqual(self.client.get(self.url).context["article_count"], 2)

    def test_reference_stays_the_first_article_when_a_newer_coverage_exists(self):
        story = Story.objects.create()
        anchor = self.article("Anuncio original", story=story, age=4)
        self.article("Ampliación más reciente", story=story)
        pending = self.article("Otra cobertura pendiente", index=1)
        def group(batch, candidates):
            self.assertEqual([article.pk for article in candidates], [anchor.pk])
            return [{"story_id": story.pk, "article_ids": [pending.pk]}]
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=group):
            call_command("group_news_ai", stdout=StringIO())

    def test_concurrent_reassignment_aborts_instead_of_overwriting_it(self):
        pending = self.article("Pendiente")
        concurrent = Story.objects.create()
        def group(batch, candidates):
            Article.objects.filter(pk=pending.pk).update(story=concurrent)
            return [{"story_id": 0, "article_ids": [pending.pk]}]
        with patch("news.management.commands.group_news_ai.group_articles", side_effect=group):
            with self.assertRaises(CommandError):
                call_command("group_news_ai", stdout=StringIO())
        pending.refresh_from_db()
        self.assertEqual(pending.story_id, concurrent.pk)

    def test_legacy_groups_are_not_scored_before_review(self):
        self.article("Sin revisar", story=Story.objects.create(grouping_version=0))
        with patch("news.management.commands.score_news_ai.score_stories") as model:
            call_command("score_news_ai", stdout=StringIO())
            model.assert_not_called()

    def test_changed_description_or_revoked_permission_aborts_grouping(self):
        self.feeds[0].show_summary = True
        self.feeds[0].save()
        pending = self.article("Pendiente con descripción")
        for change in ("description", "permission"):
            pending.summary = "Descripción original ficticia."
            pending.save(update_fields=["summary"])
            self.feeds[0].show_summary = True
            self.feeds[0].save()
            def group(batch, candidates):
                if change == "description":
                    Article.objects.filter(pk=pending.pk).update(summary="Información nueva ficticia.")
                else:
                    Feed.objects.filter(pk=self.feeds[0].pk).update(show_summary=False)
                return [{"story_id": 0, "article_ids": [pending.pk]}]
            with self.subTest(change=change), patch(
                "news.management.commands.group_news_ai.group_articles", side_effect=group,
            ), self.assertRaisesMessage(CommandError, "Los datos cambiaron"):
                call_command("group_news_ai", stdout=StringIO())
            pending.refresh_from_db()
            self.assertIsNone(pending.story_id)

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
    def test_review_version_preserves_old_groups_and_their_articles_in_both_directions(self):
        previous = [("news", "0018_expand_categories_and_sources")]
        target = [("news", "0019_story_grouping_version")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(previous)
            old = executor.loader.project_state(previous).apps
            source = old.get_model("news", "Source").objects.create(name="Medio sintético versión")
            feed = old.get_model("news", "Feed").objects.create(
                source_id=source.pk, name="RSS", url="https://example.com/migration-version/rss",
            )
            story = old.get_model("news", "Story").objects.create(importance_score=4)
            article = old.get_model("news", "Article").objects.create(
                feed_id=feed.pk, story_id=story.pk, title="Titular sintético previo",
                original_url="https://example.com/migration-version/article",
            )
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            stored = current.get_model("news", "Story").objects.get(pk=story.pk)
            self.assertEqual(stored.grouping_version, 0)
            self.assertEqual(stored.importance_score, 4)
            self.assertEqual(current.get_model("news", "Article").objects.get(pk=article.pk).story_id, story.pk)
            self.assertEqual(current.get_model("news", "Story").objects.create().grouping_version, 1)
            executor = MigrationExecutor(connection)
            executor.migrate(previous)
            restored = executor.loader.project_state(previous).apps
            self.assertEqual(restored.get_model("news", "Article").objects.get(pk=article.pk).story_id, story.pk)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

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
