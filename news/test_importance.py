import json
import re
from datetime import datetime, timedelta, timezone as datetime_timezone
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .llm_importance import ImportanceError, score_stories, validate_scores
from .models import Article, Category, Feed, Source, Story, UserPreference


class ImportanceValidationTests(SimpleTestCase):
    def test_validates_scores_reasons_and_exact_partition(self):
        valid = {"stories": [{"story_id": 2, "score": 4, "reason": " Impacto público claro. "}]}
        self.assertEqual(validate_scores(valid, {2})[2], {"score": 4, "reason": "Impacto público claro."})
        for rows in ([], [{"story_id": 3, "score": 4, "reason": "Otro ID"}],
                     [{"story_id": 2, "score": True, "reason": "Booleano"}],
                     [{"story_id": 2, "score": 6, "reason": "Fuera de rango"}],
                     [{"story_id": 2, "score": 4, "reason": " "}],
                     [{"story_id": 2, "score": 4, "reason": "x" * 301}],
                     [valid["stories"][0], valid["stories"][0]]):
            with self.subTest(rows=rows), self.assertRaises(ImportanceError):
                validate_scores({"stories": rows}, {2})


class ImportanceAndDateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.get(slug="tecnologia")
        cls.source = Source.objects.create(name="Fuente de ensayo importancia")
        cls.feed = Feed.objects.create(source=cls.source, name="RSS", url="https://example.com/importance/rss",
                                       is_active=True, allow_ai_grouping=True)
        cls.user = get_user_model().objects.create_user(username="lector-importancia")
        UserPreference.objects.create(user=cls.user).categories.add(cls.category)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("category_news", args=[self.category.slug])

    def article(self, title, hours=1, score=None):
        story = Story.objects.create(importance_score=score, importance_reason="Razón sintética." if score else "")
        article = Article.objects.create(
            feed=self.feed, story=story, title=title, language="es",
            original_url=f"https://example.com/importance/{Article.objects.count()}",
            published_at=timezone.now() - timedelta(hours=hours), summary="Texto que nunca debe enviarse",
        )
        article.categories.add(self.category)
        return article

    def test_order_switch_explanations_and_unknowns_remain_visible(self):
        important = self.article("Avance sustancial", hours=5, score=5)
        minor = self.article("Novedad menor", hours=2, score=2)
        pending = self.article("Por evaluar", hours=1)
        self.assertEqual([a.pk for a in self.client.get(self.url).context["articles"]], [pending.pk, minor.pk, important.pk])
        response = self.client.get(self.url, {"sort": "important"})
        self.assertEqual([a.pk for a in response.context["articles"]], [important.pk, minor.pk, pending.pk])
        self.assertContains(response, "La más importante")
        self.assertContains(response, "Importancia general 5/5")
        self.assertContains(response, "Razón sintética.")
        self.assertContains(response, "Importancia pendiente de evaluación")
        self.feed.allow_ai_grouping = False
        self.feed.save()
        response = self.client.get(self.url, {"sort": "important"})
        self.assertNotContains(response, "Importancia general 5/5")
        self.assertEqual([a.pk for a in response.context["articles"]], [pending.pk, minor.pk, important.pk])

    def test_today_uses_buenos_aires_midnight_and_rolling_periods(self):
        now = datetime(2026, 10, 25, 5, 0, tzinfo=datetime_timezone.utc)
        with patch("django.utils.timezone.now", return_value=now):
            today = self.article("Hoy", hours=1)
            yesterday = self.article("Ayer local", hours=3)
            older = self.article("Hace dos días", hours=48)
            future = self.article("Fecha futura", hours=-1)
            expected = {"today": [today.pk], "24h": [today.pk, yesterday.pk],
                        "3d": [today.pk, yesterday.pk, older.pk], "7d": [today.pk, yesterday.pk, older.pk]}
            for period, ids in expected.items():
                response = self.client.get(self.url, {"period": period})
                self.assertEqual([a.pk for a in response.context["articles"]], ids)
                self.assertNotContains(response, future.title)
            for params in ({"period": "bad"}, {"sort": "bad"}):
                response = self.client.get(self.url, params)
                self.assertTrue(response.context["filter_form"].errors)
                self.assertEqual(response.context["articles"], [])

    def test_importance_cursor_combines_date_and_filters_without_duplicates(self):
        for index in range(25):
            self.article(f"Noticia {index}", hours=index + 1, score=index % 5 + 1)
        self.article("Antigua aunque importante", hours=100, score=5)
        first = self.client.get(self.url, {"sort": "important", "period": "3d", "source": self.source.pk})
        expected = list(Article.objects.filter(published_at__gte=timezone.now() - timedelta(days=3))
                        .order_by("-story__importance_score", "-published_at", "-pk").values_list("pk", flat=True))
        seen = [a.pk for a in first.context["articles"]]
        url = first.context["next_url"]
        old_url = url
        while url:
            data = self.client.get(url, HTTP_ACCEPT="application/json").json()
            seen.extend(map(int, re.findall(r'data-article-id="(\d+)"', data["html"])))
            url = data["next_url"]
        self.assertEqual(seen, expected)
        self.assertEqual(self.client.get(old_url + "&period=7d", HTTP_ACCEPT="application/json").status_code, 400)
        self.assertEqual(self.client.get(old_url + "&sort=", HTTP_ACCEPT="application/json").status_code, 400)

    def test_today_cursor_expires_on_local_day_change(self):
        noon = datetime(2026, 10, 25, 15, 0, tzinfo=datetime_timezone.utc)
        with patch("django.utils.timezone.now", return_value=noon):
            for index in range(11):
                self.article(f"Hoy {index}")
            url = self.client.get(self.url, {"period": "today"}).context["next_url"]
        with patch("django.utils.timezone.now", return_value=noon + timedelta(days=1)):
            self.assertEqual(self.client.get(url, HTTP_ACCEPT="application/json").status_code, 400)

    def test_command_caches_then_reassesses_new_coverages_and_failure_keeps_score(self):
        article = self.article("Anuncio importante")
        scores = {article.story_id: {"score": 4, "reason": "Consecuencias amplias."}}
        with patch("news.management.commands.score_news_ai.score_stories", return_value=scores) as model:
            call_command("score_news_ai", stdout=StringIO())
            call_command("score_news_ai", stdout=StringIO())
            self.assertEqual(model.call_count, 1)
            article.story.refresh_from_db()
            self.assertEqual(article.story.importance_score, 4)
            call_command("score_news_ai", force=True, stdout=StringIO())
            self.assertEqual(model.call_count, 2)
            with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(seconds=1)):
                Article.objects.create(feed=self.feed, story=article.story, title="Cobertura nueva",
                                       original_url="https://example.com/new-coverage", published_at=timezone.now())
                call_command("score_news_ai", stdout=StringIO())
            self.assertEqual(model.call_count, 3)
        with patch("news.management.commands.score_news_ai.score_stories", side_effect=ImportanceError("Error")):
            with self.assertRaises(CommandError):
                call_command("score_news_ai", force=True, stdout=StringIO())
        article.story.refresh_from_db()
        self.assertEqual(article.story.importance_score, 4)

    def test_payload_does_not_send_bodies_or_users_and_excludes_unauthorized_feeds(self):
        article = self.article("Titular seguro")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "clave-sintetica"}), patch("news.llm_importance.genai.Client") as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.return_value.text = json.dumps({"stories": [{"story_id": article.story_id, "score": 3, "reason": "Alcance sectorial."}]})
            score_stories({article.story_id: [article]})
            payload = generate.call_args.kwargs["contents"]
            self.assertNotIn(article.summary, payload)
            self.assertNotIn(article.original_url, payload)
            self.assertNotIn(self.user.username, payload)
            self.assertEqual(client.call_args.kwargs["http_options"].timeout, 60_000)
        self.feed.allow_ai_grouping = False
        self.feed.save()
        with patch("news.management.commands.score_news_ai.score_stories") as model:
            call_command("score_news_ai", stdout=StringIO())
            model.assert_not_called()

    def test_database_rejects_out_of_range_importance(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Story.objects.create(importance_score=6)

    @skipUnless(connection.vendor == "postgresql", "Relevancia requiere PostgreSQL")
    def test_search_can_choose_relevance_recency_or_importance(self):
        older = self.article("Robots y empresas", hours=10, score=4)
        newer = self.article("Las empresas anuncian proyectos y robots de prueba", hours=1, score=2)
        pending = self.article("Robots y empresas sin evaluar", hours=2)
        expected = {"": [older.pk, pending.pk, newer.pk], "recent": [newer.pk, pending.pk, older.pk],
                    "important": [older.pk, newer.pk, pending.pk]}
        for sort, ids in expected.items():
            response = self.client.get(self.url, {"q": "robots empresas", "sort": sort})
            self.assertEqual([a.pk for a in response.context["articles"]], ids)
