import os
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, TestCase
from django.core.management import call_command
from io import StringIO
from django.utils import timezone

from . import ollama
from .llm_classification import ClassificationError, classify_batch
from .llm_grouping import GroupingError, group_articles, request_groups
from .llm_importance import score_stories
from .llm_briefing import summarize_articles


class OllamaTests(SimpleTestCase):
    def setUp(self):
        ollama._embedding_cache.clear()

    def article(self, pk=5):
        return SimpleNamespace(pk=pk, title="Abre un hospital municipal", language="es", story_id=None,
                               published_at=timezone.now(), feed=SimpleNamespace(
                                   source=SimpleNamespace(name="Prueba"), show_summary=False))

    @patch.dict(os.environ, {}, clear=True)
    def test_disabled_by_default(self):
        self.assertFalse(ollama.enabled())

    @patch("news.ollama.httpx.post")
    def test_loopback_schema_complete_json_and_no_proxy(self, post):
        post.return_value = httpx.Response(200, request=httpx.Request("POST", "http://127.0.0.1"),
                                          json={"done": True, "done_reason": "stop", "response": '{"ok":true}'})
        schema = {"type": "object"}
        self.assertEqual(ollama.request_json("datos ficticios", schema, "test"), {"ok": True})
        args, kwargs = post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:11434/api/generate")
        self.assertFalse(kwargs["trust_env"])
        self.assertEqual(kwargs["json"]["format"], schema)
        self.assertFalse(kwargs["json"]["think"])

    @patch("news.ollama.httpx.post")
    def test_truncated_and_duplicate_json_are_rejected(self, post):
        for data in ({"done": True, "done_reason": "length", "response": '{}'},
                     {"done": True, "done_reason": "stop", "response": '{"id":1,"id":2}'}):
            with self.subTest(data=data):
                post.return_value = httpx.Response(200, request=httpx.Request("POST", "http://127.0.0.1"), json=data)
                with self.assertRaises(ollama.LocalModelError):
                    ollama.request_json("ficticio", {}, "test")

    @patch("news.ollama.httpx.post")
    def test_oversized_prompt_is_not_silently_truncated(self, post):
        with self.assertRaises(ollama.LocalModelError) as caught:
            ollama.request_json("x" * 24001, {}, "test")
        self.assertEqual(caught.exception.code, "request_too_large")
        post.assert_not_called()

    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1"}, clear=True)
    @patch("news.llm_classification.genai.Client")
    @patch("news.ollama.request_json")
    def test_classification_without_api_key_retains_validation_and_model(self, local, cloud):
        article = SimpleNamespace(pk=5, title="Torneo de golf", language="es", feed=SimpleNamespace(source=SimpleNamespace(name="Prueba")))
        local.return_value = {"articles": [{"article_id": 5, "categories": ["deportes"]}]}
        result = classify_batch([article], ["deportes"])
        self.assertEqual(result, {5: ["deportes"]})
        self.assertEqual(result.model, "ollama:qwen3:4b-instruct")
        cloud.assert_not_called()
        local.return_value = {"articles": [{"article_id": 999, "categories": ["deportes"]}]}
        with self.assertRaises(ClassificationError):
            classify_batch([article], ["deportes"])
        cloud.assert_not_called()

    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1", "GEMINI_API_KEY": "synthetic"}, clear=True)
    @patch("news.llm_classification.genai.Client")
    @patch("news.ollama.request_json", side_effect=ollama.LocalModelError("connection_or_response"))
    def test_unavailable_local_uses_cloud_once_with_assigned_key(self, local, cloud):
        article = SimpleNamespace(pk=5, title="Golf", language="es", feed=SimpleNamespace(source=SimpleNamespace(name="Prueba")))
        cloud.return_value.models.generate_content.return_value.text = '{"articles":[{"article_id":5,"categories":["deportes"]}]}'
        self.assertEqual(classify_batch([article], ["deportes"]), {5: ["deportes"]})
        self.assertEqual(cloud.call_args.kwargs["api_key"], "synthetic")
        local.assert_called_once()

    @patch("news.ollama.request_json", side_effect=ollama.LocalModelError("request_too_large"))
    def test_grouping_reduces_candidate_window(self, local):
        with self.assertRaises(GroupingError) as caught:
            request_groups("datos", {}, "", provider="ollama")
        self.assertTrue(caught.exception.reduce_candidates)

    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1"}, clear=True)
    @patch("news.ollama.request_json")
    def test_grouping_keeps_independent_identity_audit_and_attribution(self, local):
        first, second = self.article(5), self.article(6)
        local.side_effect = [{"groups": {"5": "new:5", "6": "new:5"}},
                             {"decisions": {"6": {"same_event": False, "reason": "Hechos diferentes"}}}]
        result = group_articles([first, second], [])
        self.assertEqual({tuple(row["article_ids"]) for row in result}, {(5,), (6,)})
        self.assertEqual(result.model, "ollama:qwen3:4b-instruct")
        self.assertEqual(local.call_count, 2)

    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1"}, clear=True)
    @patch("news.ollama.request_json")
    def test_importance_preserves_validation_and_model(self, local):
        local.side_effect = [{"stories": [{"story_id": 8, "score": 2, "reason": "Impacto local con evidencia limitada."}]},
                             {"decisions": {"8": {"reason": "Se limita al hecho local aportado.", "supported": True}}}]
        result = score_stories({8: [self.article()]})
        self.assertEqual(result[8]["score"], 2)
        self.assertEqual(result.model, "ollama:qwen3:4b-instruct")

    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1"}, clear=True)
    @patch("news.ollama.request_json")
    def test_briefing_preserves_category_reference_and_model(self, local):
        article = self.article()
        article.categories = SimpleNamespace(all=lambda: [SimpleNamespace(slug="salud", name="Salud")])
        article.llm_categories = SimpleNamespace(all=lambda: [])
        local.side_effect = [{"items": {"salud": {"text": "Una nueva instalación municipal amplía la atención sanitaria local.",
                                                   "article_ids": [5], "importance_score": 3}}},
                             {"decisions": {"salud": {"reason": "La apertura está en el titular.", "supported": True}}}]
        result = summarize_articles([article])
        self.assertEqual(result.model, "ollama:qwen3:4b-instruct")
        self.assertEqual(result[0]["article_ids"], [5])

    @patch("news.ollama.request_json", return_value={"decisions": {"8": {"reason": "Cantidad no aportada.", "supported": False}}})
    def test_unsupported_claims_are_rejected(self, local):
        with self.assertRaises(ollama.LocalModelError) as caught:
            ollama.audit_texts({"8": {"source": "Inauguran un hospital", "text": "Atenderá a diez mil habitantes"}}, "importance")
        self.assertEqual(caught.exception.code, "unsupported_text")

    @patch("news.ollama.httpx.post")
    def test_semantic_candidates_are_ranked_cached_and_bounded(self, post):
        query = SimpleNamespace(title="Hospital nuevo")
        candidates = [SimpleNamespace(title=f"Titular {i}", story_id=i) for i in range(1, 9)]
        vectors = [[1., 0.]] + [[float(i), 1.] for i in range(1, 9)]
        post.return_value = httpx.Response(200, request=httpx.Request("POST", "http://127.0.0.1"), json={"embeddings": vectors})
        selected = ollama.shortlist_candidates([query], candidates)
        self.assertEqual([row.story_id for row in selected], [8, 7, 6, 5])
        self.assertEqual(len(selected), 4)
        self.assertFalse(post.call_args.kwargs["json"]["truncate"])
        ollama.shortlist_candidates([query], candidates)
        post.assert_called_once()

    @patch("news.ollama.httpx.post")
    def test_invalid_embedding_is_not_used_for_grouping(self, post):
        post.return_value = httpx.Response(200, request=httpx.Request("POST", "http://127.0.0.1"), json={"embeddings": [[0., 0.]] * 6})
        with self.assertRaises(ollama.LocalModelError):
            ollama.shortlist_candidates([SimpleNamespace(title="Entrada")],
                                         [SimpleNamespace(title=f"T{i}", story_id=i) for i in range(5)])


class LocalPersistenceTests(TestCase):
    @patch.dict(os.environ, {"AI_LOCAL_FIRST": "1"}, clear=True)
    @patch("news.ollama.request_json")
    def test_commands_persist_actual_local_provider_without_api_keys(self, local):
        from .models import Article, Category, Feed, Source
        category = Category.objects.get(slug="deportes")
        feed = Feed.objects.create(source=Source.objects.create(name="Medio sintético local"),
                                   name="Prueba", url="https://example.com/local-feed", is_active=True,
                                   allow_ai_grouping=True)
        article = Article.objects.create(feed=feed, title="Final del torneo de golf",
                                          original_url="https://example.com/local-news", published_at=timezone.now())
        article.categories.add(category)
        local.return_value = {"articles": [{"article_id": article.pk, "categories": ["deportes"]}]}
        call_command("classify_news_ai", limit=1, stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.llm_model, "ollama:qwen3:4b-instruct")
        local.return_value = {"groups": {str(article.pk): f"new:{article.pk}"}}
        call_command("group_news_ai", limit=1, stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.story.llm_model, "ollama:qwen3:4b-instruct")
        pk = article.story_id
        local.side_effect = [{"stories": [{"story_id": pk, "score": 2, "reason": "Es un resultado deportivo de alcance acotado."}]},
                             {"decisions": {str(pk): {"reason": "El titular sólo menciona un torneo.", "supported": True}}}]
        call_command("score_news_ai", limit=1, stdout=StringIO())
        article.story.refresh_from_db()
        self.assertEqual(article.story.importance_model, "ollama:qwen3:4b-instruct")


@patch.dict(os.environ, {"AI_API_FIRST": "true", "AI_LOCAL_FIRST": "true",
                         "GEMINI_API_KEY": "synthetic", "OLLAMA_FALLBACK_LIMIT": "10"}, clear=True)
class ApiFirstTests(SimpleTestCase):
    def setUp(self):
        ollama._fallback_used.clear()

    def article(self, pk=5):
        article = OllamaTests.article(self, pk)
        article.categories = SimpleNamespace(all=lambda: [SimpleNamespace(slug="salud", name="Salud")])
        article.llm_categories = SimpleNamespace(all=lambda: [])
        return article

    @patch("news.ollama.request_json")
    @patch("news.llm_classification.genai.Client")
    def test_healthy_api_does_not_call_pc_even_when_local_first_also_set(self, cloud, local):
        cloud.return_value.models.generate_content.return_value.text = '{"articles":[{"article_id":5,"categories":["salud"]}]}'
        self.assertEqual(classify_batch([self.article()], ["salud"]), {5: ["salud"]})
        local.assert_not_called()
        self.assertFalse(ollama.local_first())

    @patch("news.ollama.request_json")
    @patch("news.llm_classification.genai.Client")
    def test_api_failure_uses_validated_local_and_keeps_model(self, cloud, local):
        order = []
        def unavailable(**kwargs):
            order.append("api")
            raise RuntimeError("quota")
        cloud.side_effect = unavailable
        def response(*args):
            order.append("local")
            return {"articles": [{"article_id": 5, "categories": ["salud"]}]}
        local.side_effect = response
        result = classify_batch([self.article()], ["salud"])
        self.assertEqual(order, ["api", "local"])
        self.assertEqual(result.model, ollama.model_name())
        local.return_value = {"articles": [{"article_id": 999, "categories": []}]}
        local.side_effect = None
        with self.assertRaises(ClassificationError):
            classify_batch([self.article()], ["salud"])

    @patch("news.ollama.request_json", side_effect=ollama.LocalModelError("bridge_unavailable"))
    @patch("news.llm_classification.genai.Client", side_effect=RuntimeError("quota"))
    def test_both_unavailable_stop_without_retrying_api(self, cloud, local):
        with self.assertRaises(ClassificationError):
            classify_batch([self.article()], ["salud"])
        cloud.assert_called_once()
        local.assert_called_once()

    @patch("news.ollama.request_json")
    @patch("news.llm_classification.genai.Client", side_effect=RuntimeError("quota"))
    def test_ten_fallback_items_split_into_small_calls_then_budget_stops_cpu(self, cloud, local):
        def response(prompt, schema, task):
            ids = schema["properties"]["articles"]["items"]["properties"]["article_id"]["enum"]
            self.assertLessEqual(len(ids), 3)
            return {"articles": [{"article_id": pk, "categories": ["salud"]} for pk in ids]}
        local.side_effect = response
        self.assertEqual(len(classify_batch([self.article(pk) for pk in range(10)], ["salud"])), 10)
        self.assertEqual(local.call_count, 4)
        with self.assertRaisesRegex(ClassificationError, "fallback_limit"):
            classify_batch([self.article(20)], ["salud"])
        self.assertEqual(local.call_count, 4)

    @patch("news.ollama.audit_texts", side_effect=ollama.LocalModelError("unsupported_text"))
    @patch("news.ollama.request_json")
    @patch("news.llm_importance.genai.Client", side_effect=RuntimeError("quota"))
    def test_importance_fallback_does_not_bypass_text_audit(self, cloud, local, audit):
        from .llm_importance import ImportanceError
        local.return_value = {"stories": [{"story_id": 8, "score": 2, "reason": "Impacto local limitado."}]}
        with self.assertRaisesRegex(ImportanceError, "unsupported_text"):
            score_stories({8: [self.article()]})
        audit.assert_called_once()
        cloud.assert_called_once()

    @patch("news.ollama.shortlist_candidates", return_value=[])
    @patch("news.llm_grouping.request_groups")
    def test_grouping_api_failure_then_local_identity_audit(self, request, shortlist):
        def response(prompt, schema, key, *, provider="gemini"):
            if provider == "gemini":
                raise GroupingError("quota", retryable=False, fallback_allowed=False)
            if "groups" in schema["properties"]:
                return {"groups": [{"story_id": 0, "article_ids": [5, 6]}]}
            return {"decisions": [{"article_id": 6, "same_event": False, "reason": "Hechos distintos."}]}
        request.side_effect = response
        result = group_articles([self.article(5), self.article(6)], [])
        self.assertEqual([row["article_ids"] for row in result], [[5], [6]])
        self.assertEqual(result.model, ollama.model_name())
        self.assertEqual([call.kwargs.get("provider", "gemini") for call in request.call_args_list],
                         ["gemini", "ollama", "ollama"])

    @patch("news.ollama.shortlist_candidates")
    @patch("news.llm_grouping.request_groups", return_value={"groups": [{"story_id": 0, "article_ids": [5]}]})
    def test_grouping_healthy_api_does_not_compute_local_embeddings(self, request, shortlist):
        group_articles([self.article()], [])
        shortlist.assert_not_called()

    @patch("news.ollama.audit_texts")
    @patch("news.ollama.request_json")
    @patch("news.llm_briefing._gemini_summary")
    def test_briefing_api_sees_full_candidates_and_local_fallback_is_smaller(self, cloud, local, audit):
        import json
        from .llm_briefing import BriefingError
        articles = [self.article(pk) for pk in range(5, 25)]
        seen = []
        def failed(prompt, schema, key):
            seen.append(len(json.loads(prompt.split("\n", 1)[1])["articles"]))
            raise BriefingError("quota", "configuration")
        cloud.side_effect = failed
        local.return_value = {"items": {"salud": {"text": "Se anunció la apertura de un hospital en el municipio.",
                                                   "importance_score": 2, "article_ids": [7]}}}
        result = summarize_articles(articles, previous_selection={"salud": 7})
        self.assertEqual(seen, [20])
        local_payload = json.loads(local.call_args.args[0].split("\n", 1)[1])
        self.assertEqual([row["article_id"] for row in local_payload["articles"]], [7])
        self.assertEqual(result.model, ollama.model_name())
        audit.assert_called_once()


    @patch("news.management.commands.group_news_ai.ollama.shortlist_candidates", return_value=[])
    @patch("news.management.commands.group_news_ai.group_articles")
    def test_command_local_fallback_considers_all_candidates_after_cloud_blocks_fail(self, group, shortlist):
        from .management.commands.group_news_ai import Command
        from .llm_transport import ModelList
        candidates = [SimpleNamespace(story_id=pk) for pk in range(200)]
        def propose(batch, anchors, **kwargs):
            if kwargs.get("provider") == "ollama":
                return ModelList([{"story_id": 0, "article_ids": [5]}], ollama.model_name())
            self.assertFalse(kwargs["allow_local"])
            if anchors[0].story_id == 100:
                raise GroupingError("quota", retryable=False)
            return [{"story_id": 0, "article_ids": [5]}]
        group.side_effect = propose
        result, limit = Command().propose_batch([self.article()], candidates, 100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["_model"], ollama.model_name())
        self.assertEqual(shortlist.call_args.args[1], candidates)
        shortlist.assert_called_once()
        self.assertEqual(ollama._fallback_used["grouping"], 1)
        self.assertEqual(group.call_count, 3)

    @patch.dict(os.environ, {"GROQ_API_KEY": "synthetic"})
    @patch("news.ollama.request_json")
    @patch("news.llm_briefing.request_backup")
    @patch("news.llm_briefing.backup_providers", return_value=["groq"])
    @patch("news.llm_briefing._gemini_summary")
    def test_existing_api_backup_is_attempted_before_ollama(self, cloud, providers, backup, local):
        from .llm_briefing import BriefingError
        cloud.side_effect = BriefingError("quota", "quota")
        backup.return_value = {"items": {"salud": {"text": "Se anunció la apertura de un hospital municipal.",
                                                    "importance_score": 2, "article_ids": [5]}}}
        result = summarize_articles([self.article()])
        self.assertTrue(result.model.startswith("groq:"))
        backup.assert_called_once()
        local.assert_not_called()


    def test_small_fallback_budget_uses_batches_that_can_fit(self):
        self.assertEqual(ollama.batch_size(), 10)
        with patch.dict(os.environ, {"OLLAMA_FALLBACK_LIMIT": "3"}):
            self.assertEqual(ollama.batch_size(), 3)
