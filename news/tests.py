from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.error import HTTPError

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .ingestion import ingest_feed, permitted_image
from .browsing import ILLUSTRATION_POOLS, article_illustration
from .llm_classification import ClassificationError, classify_batch
from .models import Article, ArticleOrigin, Category, Feed, SavedArticle, Source, UserPreference
from .search import search_articles


class IllustrationTests(SimpleTestCase):
    def test_each_category_has_variety_and_existing_local_assets(self):
        for slug, choices in ILLUSTRATION_POOLS.items():
            with self.subTest(category=slug):
                paths = {
                    article_illustration(SimpleNamespace(pk=key, has_verified_story=False), slug)
                    for key in range(1, len(choices) + 1)
                }
                self.assertEqual(len(paths), len(choices))
                self.assertGreaterEqual(len(paths), 2)
                for path in paths:
                    self.assertIsNotNone(finders.find(path))

    def test_verified_story_keeps_image_when_representative_changes(self):
        first = SimpleNamespace(pk=11, story_id=8, has_verified_story=True)
        second = SimpleNamespace(pk=12, story_id=8, has_verified_story=True)
        self.assertEqual(article_illustration(first, "deportes"), article_illustration(second, "deportes"))
        second.has_verified_story = False
        self.assertNotEqual(article_illustration(first, "deportes"), article_illustration(second, "deportes"))
        self.assertEqual(article_illustration(first, "unknown"), "news/images/geopolitica.webp")


class AIResponseTests(SimpleTestCase):
    def test_rejects_unrequested_article_id(self):
        article = SimpleNamespace(
            pk=7, title="Titular", language="es",
            feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")),
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"}):
            with patch("news.llm_classification.genai.Client") as client:
                client.return_value.models.generate_content.return_value.text = (
                    '{"articles":[{"article_id":8,"categories":["economia"]}]}'
                )
                with self.assertRaises(ClassificationError):
                    classify_batch([article], ["economia"])
                schema = client.return_value.models.generate_content.call_args.kwargs["config"].response_json_schema
                rows = schema["properties"]["articles"]
                self.assertEqual((rows["minItems"], rows["maxItems"]), (1, 1))
                self.assertEqual(rows["items"]["properties"]["article_id"]["enum"], [7])
                self.assertEqual(rows["items"]["properties"]["categories"]["maxItems"], 3)

    def test_invalid_category_shapes_have_safe_diagnostics(self):
        import json
        article = SimpleNamespace(pk=7, title="Titular privado de ensayo", language="es",
                                  feed=SimpleNamespace(source=SimpleNamespace(name="Fuente")))
        cases = [(None, "categories"), ([["economia"]], "category"),
                 (["private-category"], "category"), (["economia", "economia"], "repeated_category"),
                 (["economia"] * 4, "too_many_categories")]
        with patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"}), patch("news.llm_classification.genai.Client") as client:
            for categories, reason in cases:
                client.return_value.models.generate_content.return_value.text = json.dumps({"articles": [{
                    "article_id": 7, "categories": categories,
                }]})
                with self.subTest(reason=reason), self.assertRaisesRegex(ClassificationError, f"reason={reason}") as caught:
                    classify_batch([article], ["economia"])
                self.assertNotIn("private-category", str(caught.exception))


class AIClassificationTests(TestCase):
    def test_command_stores_ai_result_without_changing_rule_categories(self):
        source = Source.objects.create(name="Fuente de prueba")
        feed = Feed.objects.create(
            source=source, name="RSS", url="https://example.com/ai-rss", is_active=True,
        )
        rule_category = Category.objects.get(slug="economia")
        ai_category = Category.objects.get(slug="inteligencia-artificial")
        article = Article.objects.create(
            feed=feed, title="La IA impulsa un nuevo desarrollo",
            original_url="https://example.com/ai", published_at=timezone.now(),
        )
        article.categories.add(rule_category)
        with patch("news.management.commands.classify_news_ai.classify_batch", return_value={
            article.pk: [ai_category.slug],
        }):
            call_command("classify_news_ai")
        article.refresh_from_db()
        self.assertCountEqual(article.categories.all(), [rule_category])
        self.assertCountEqual(article.llm_categories.all(), [ai_category])
        self.assertIsNotNone(article.llm_classified_at)

        with patch("news.management.commands.classify_news_ai.classify_batch") as classify:
            call_command("classify_news_ai")
        classify.assert_not_called()

    def test_api_failure_keeps_article_pending(self):
        source = Source.objects.create(name="Fuente de prueba")
        feed = Feed.objects.create(
            source=source, name="RSS", url="https://example.com/ai-rss", is_active=True,
        )
        article = Article.objects.create(
            feed=feed, title="Titular pendiente",
            original_url="https://example.com/pendiente", published_at=timezone.now(),
        )
        with patch("news.management.commands.classify_news_ai.classify_batch", side_effect=ClassificationError("cuota")):
            with self.assertRaises(CommandError):
                call_command("classify_news_ai")
        article.refresh_from_db()
        self.assertIsNone(article.llm_classified_at)


class RegistrationTests(TestCase):
    def test_name_is_required_and_first_given_name_is_used_in_welcome(self):
        registration = {
            "username": "lectora_nueva",
            "password1": "ClaveSegura2026!",
            "password2": "ClaveSegura2026!",
        }
        response = self.client.post(reverse("register"), registration)
        self.assertEqual(response.status_code, 200)
        self.assertIn("first_name", response.context["form"].errors)
        self.assertFalse(get_user_model().objects.filter(username="lectora_nueva").exists())

        response = self.client.post(reverse("register"), {**registration, "first_name": "  María   José  "})
        self.assertRedirects(response, reverse("preferences"))
        user = get_user_model().objects.get(username="lectora_nueva")
        self.assertEqual(user.first_name, "María José")
        response = self.client.get(reverse("news_feed"))
        self.assertEqual(response.context["display_name"], "María")
        self.assertContains(response, ", María")

    def test_existing_account_without_name_keeps_username_as_welcome(self):
        user = get_user_model().objects.create_user(username="cuenta_antigua")
        self.client.force_login(user)
        response = self.client.get(reverse("news_feed"))
        self.assertEqual(response.context["display_name"], "cuenta_antigua")


class NewsFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="lector")
        cls.category = Category.objects.create(name="Tema de prueba", slug="tema-prueba")
        cls.other_category = Category.objects.create(name="Otro tema", slug="otro-tema")
        cls.source = Source.objects.create(name="Fuente A")
        cls.other_source = Source.objects.create(name="Fuente B")
        cls.feed = Feed.objects.create(
            source=cls.source, name="Feed A", url="https://example.com/rss-a", is_active=True,
        )
        cls.other_feed = Feed.objects.create(
            source=cls.other_source, name="Feed B", url="https://example.com/rss-b", is_active=True,
        )
        preference = UserPreference.objects.create(user=cls.user)
        preference.categories.add(cls.category)

    def setUp(self):
        self.client.force_login(self.user)

    def article(self, title, *, feed=None, language="es", age=1, category=None):
        article = Article.objects.create(
            feed=feed or self.feed, title=title,
            original_url=f"https://example.com/{title}", language=language,
            published_at=timezone.now() - timedelta(days=age),
        )
        article.categories.add(category or self.category)
        return article

    @property
    def url(self):
        return reverse("category_news", args=[self.category.slug])

    def titles(self, response):
        return [article.title for article in response.context["articles"]]

    def test_requires_login_and_selected_category(self):
        self.assertEqual(self.client.get(reverse("category_news", args=[self.other_category.slug])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.get(reverse("news_feed")).status_code, 302)

    def test_portal_has_stable_categories_counts_and_empty_state(self):
        preference = UserPreference.objects.get(user=self.user)
        preference.categories.add(self.other_category)
        article = self.article("visible")
        article.categories.add(self.other_category)
        response = self.client.get(reverse("news_feed"))
        self.assertEqual([x["category"] for x in response.context["sections"]], [self.other_category, self.category])
        self.assertEqual([x["article_count"] for x in response.context["sections"]], [1, 1])
        self.assertNotContains(response, article.title)
        self.assertContains(response, self.url)
        Article.objects.all().delete()
        self.assertContains(self.client.get(reverse("news_feed")), "Todavía no hay noticias")
        preference.categories.clear()
        self.assertContains(self.client.get(reverse("news_feed")), "Elegí tus categorías")

    def test_classification_preference_switches_visible_articles(self):
        by_rules = self.article("por-reglas")
        by_ai = self.article("por-ia")
        by_ai.categories.clear()
        by_ai.llm_categories.add(self.category)
        preference = UserPreference.objects.get(user=self.user)
        for mode, expected in (("both", [by_rules.title, by_ai.title]), ("rules", [by_rules.title]), ("ai", [by_ai.title])):
            preference.classification_mode = mode
            preference.save()
            self.assertCountEqual(self.titles(self.client.get(self.url)), expected)

    def test_classification_mode_is_saved_with_preferences(self):
        self.client.post(reverse("preferences"), {"categories": [self.category.pk], "classification_mode": "ai"})
        self.assertEqual(UserPreference.objects.get(user=self.user).classification_mode, "ai")

    def test_filters_preferences_active_feeds_and_retention(self):
        expected = self.article("visible")
        self.article("ingles", language="en")
        self.article("otra-fuente", feed=self.other_feed)
        self.article("otro-tema", category=self.other_category)
        self.article("vieja", age=15)
        inactive = Feed.objects.create(source=self.source, name="Inactivo", url="https://example.com/inactive")
        self.article("inactiva", feed=inactive)
        response = self.client.get(self.url, {"source": self.source.pk, "language": "es"})
        self.assertEqual(response.context["articles"], [expected])
        self.assertTrue(response.context["filters_active"])
        self.assertContains(response, 'value="es" selected')

    def test_invalid_and_empty_filters_do_not_expose_results(self):
        self.article("visible")
        self.article("ingles", language="en", feed=self.other_feed)
        for query in ({"source": "abc"}, {"source": "999999"}, {"language": "zz"}):
            response = self.client.get(self.url, query)
            self.assertTrue(response.context["filter_form"].errors)
            self.assertEqual(response.context["articles"], [])
        response = self.client.get(self.url, {"source": self.source.pk, "language": "en"})
        self.assertEqual(response.context["articles"], [])
        self.assertContains(response, "No hay noticias con estos filtros")

    def test_filter_applies_before_batch_limit(self):
        older = self.article("ingles-antigua", language="en", age=10)
        for index in range(11):
            self.article(f"espanol-{index}")
        self.assertEqual(self.client.get(self.url, {"language": "en"}).context["articles"], [older])
        self.assertEqual(len(self.client.get(self.url).context["articles"]), 10)

    def test_initial_batch_and_unique_editorial_opening(self):
        for count in (0, 10, 11, 28):
            Article.objects.all().delete()
            for index in range(count):
                self.article(f"noticia-{index}")
            response = self.client.get(self.url)
            self.assertEqual(len(response.context["articles"]), min(count, 10))
            self.assertEqual(response.content.count(b" article-lead"), int(count > 0))
            self.assertEqual(bool(response.context["next_url"]), count > 10)
            if count > 10:
                batch = self.client.get(response.context["next_url"], HTTP_ACCEPT="application/json")
                self.assertEqual(batch.status_code, 200)
                self.assertEqual(batch.json()["html"].count('data-article-id='), min(count - 10, 9))
                self.assertNotIn("article-lead", batch.json()["html"])

    def test_cursor_ties_inserts_deletions_and_no_duplicates(self):
        import re
        for index in range(28):
            self.article(f"noticia-{index}")
        Article.objects.all().update(published_at=timezone.now())
        expected = list(Article.objects.order_by("-id").values_list("id", flat=True))
        first = self.client.get(self.url)
        seen = [article.pk for article in first.context["articles"]]
        self.article("nueva-durante-lectura", age=0)
        Article.objects.filter(pk=expected[15]).delete()
        expected.remove(expected[15])
        url = first.context["next_url"]
        for _ in range(5):
            if not url:
                break
            response = self.client.get(url, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            seen.extend(map(int, re.findall(r'data-article-id="(\d+)"', data["html"])))
            url = data["next_url"]
        self.assertEqual(seen, expected)
        self.assertEqual(len(seen), len(set(seen)))

    def test_cursor_rejects_tampering_changed_filters_and_expiry(self):
        for index in range(11):
            self.article(f"noticia-{index}")
        url = self.client.get(self.url).context["next_url"]
        self.assertEqual(self.client.get(url + "&language=es", HTTP_ACCEPT="application/json").status_code, 400)
        from django.http import QueryDict
        query = QueryDict(urlsplit(url).query, mutable=True)
        query["cursor"] += "tampered"
        self.assertEqual(self.client.get(self.url + "?" + query.urlencode(), HTTP_ACCEPT="application/json").status_code, 400)
        with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 15 * 86400):
            self.assertEqual(self.client.get(url, HTTP_ACCEPT="application/json").status_code, 400)
        self.assertEqual(self.client.get(self.url, {"visible": "9" * 5000}, HTTP_ACCEPT="application/json").status_code, 400)

    def test_regular_navigation_restores_loaded_prefix_and_filters(self):
        for index in range(23):
            self.article(f"noticia-{index}")
        first = self.client.get(self.url, {"language": "es"})
        url = first.context["next_url"]
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["language"], ["es"])
        restored = self.client.get(url)
        self.assertEqual(len(restored.context["articles"]), 19)
        self.assertEqual(restored.content.count(b" article-lead"), 1)
        self.assertEqual(len(self.client.get(self.url, {"visible": 19}).context["articles"]), 19)
        self.assertEqual(len(self.client.get(self.url).context["articles"]), 10)

    def test_original_links_and_revocable_image_permission(self):
        article = self.article("con-foto")
        article.image_url, article.image_credit = "https://example.com/photo.jpg", "Fotógrafa de prueba"
        article.save()
        self.assertNotContains(self.client.get(self.url), article.image_url)
        self.feed.show_images = True
        self.feed.save()
        response = self.client.get(self.url)
        self.assertContains(response, article.image_url)
        self.assertContains(response, article.image_credit)
        self.assertContains(response, 'target="_blank" rel="noopener"')
        self.feed.show_images = False
        self.feed.save()
        response = self.client.get(self.url)
        self.assertNotContains(response, article.image_url)
        self.assertContains(response, "Imagen ilustrativa")

    def test_illustrations_are_stable_across_html_json_and_pagination(self):
        self.category = Category.objects.get(slug="deportes")
        UserPreference.objects.get(user=self.user).categories.add(self.category)
        for index in range(12):
            self.article(f"deporte-{index}")
        response = self.client.get(self.url)
        first_rows = response.context["articles"]
        self.assertEqual(len({row.fallback_image for row in first_rows}), 3)
        json_html = self.client.get(self.url, HTTP_ACCEPT="application/json").json()["html"]
        for row in first_rows:
            expected = article_illustration(row, "deportes")
            self.assertContains(response, f'data-fallback="/static/{expected}"')
            self.assertIn(f'data-fallback="/static/{expected}"', json_html)
        next_url = response.context["next_url"]
        next_page = self.client.get(next_url, HTTP_ACCEPT="application/json").json()["html"]
        self.assertIn('data-fallback="/static/news/images/illustrations/deportes-', next_page)
        self.assertEqual(next_page.count('class="article-card"'), 2)

    def test_json_bookmarks_preserve_post_security_and_are_idempotent(self):
        article = self.article("guardar-json")
        save = reverse("save_article", args=[article.pk])
        remove = reverse("remove_saved_article", args=[article.pk])
        for _ in range(2):
            self.assertEqual(self.client.post(save, HTTP_ACCEPT="application/json").json(), {"saved": True, "action": remove})
        self.assertEqual(SavedArticle.objects.filter(user=self.user, article=article).count(), 1)
        self.assertEqual(self.client.post(remove, HTTP_ACCEPT="application/json").json(), {"saved": False, "action": save})
        self.assertFalse(SavedArticle.objects.exists())
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(save, HTTP_ACCEPT="application/json").status_code, 403)


@skipUnless(connection.vendor == "postgresql", "La búsqueda de texto se verifica en PostgreSQL")
class ArticleSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="buscador")
        self.category = Category.objects.create(name="Búsqueda", slug="busqueda")
        self.other_category = Category.objects.create(name="Otro tema buscable", slug="otro-buscable")
        preference = UserPreference.objects.create(user=self.user)
        preference.categories.add(self.category)
        self.source = Source.objects.create(name="Fuente de búsqueda")
        self.feed = Feed.objects.create(source=self.source, name="RSS", url="https://example.com/search-rss", is_active=True)
        self.client.force_login(self.user)

    def article(self, title, language="es", age=0):
        article = Article.objects.create(
            feed=self.feed, title=title, language=language,
            original_url=f"https://example.com/search-{Article.objects.count()}",
            published_at=timezone.now() - timedelta(days=age),
        )
        article.categories.add(self.category)
        return article

    def results(self, text, **filters):
        response = self.client.get(reverse("category_news", args=[self.category.slug]), {"q": text, **filters})
        articles = response.context["articles"]
        return response, articles

    def test_stop_words_and_stemming_in_supported_languages(self):
        for language, title, text in (
            ("es-AR", "Las empresas investigan robots", "la empresa"),
            ("EN-us", "The researchers build robots", "a researcher"),
            ("pt_BR", "As empresas criam robôs", "a empresa"),
        ):
            with self.subTest(language=language):
                Article.objects.all().delete()
                article = self.article(title, language)
                response, results = self.results(text)
                self.assertFalse(response.context["filter_form"].errors)
                self.assertEqual([item.pk for item in results], [article.pk])

    def test_all_significant_words_must_match(self):
        match = self.article("Las empresas investigan robots")
        self.article("Las empresas anuncian inversiones")
        self.article("Robots exploran Marte")
        _, results = self.results("empresa robots")
        self.assertEqual([item.pk for item in results], [match.pk])

    def test_stop_words_only_and_punctuation_do_not_match_everything(self):
        self.article("Las empresas investigan robots")
        for text in ("de la y", "!!!", "' & | !"):
            with self.subTest(text=text):
                response, results = self.results(text)
                self.assertEqual(results, [])
                self.assertContains(response, "No hay noticias con estos filtros")

    def test_unknown_languages_use_exact_words_without_stemming(self):
        article = self.article("Robots investigan planetas", language="zz")
        self.assertEqual([item.pk for item in self.results("robots")[1]], [article.pk])
        self.assertEqual(self.results("robot")[1], [])

    def test_relevance_precedes_date_and_ties_use_date_then_id(self):
        weak = self.article("Robots estudian nuevas oportunidades para llegar a los mercados")
        strong = self.article("Robots y mercados", age=2)
        _, results = self.results("robots mercado")
        self.assertEqual([item.pk for item in results], [strong.pk, weak.pk])
        self.assertGreater(results[0].relevance, results[1].relevance)
        newer = self.article("Robots y mercados", age=1)
        tied = self.article("Robots y mercados", age=1)
        Article.objects.filter(pk=tied.pk).update(published_at=newer.published_at)
        self.assertEqual([item.pk for item in self.results("robots mercado")[1]], [tied.pk, newer.pk, strong.pk, weak.pk])

    def test_blank_search_preserves_default_sort_and_date_tiebreak(self):
        older = self.article("Robots y mercados", age=2)
        newer = self.article("Otra noticia")
        response, results = self.results("   ")
        self.assertEqual([item.pk for item in results], [newer.pk, older.pk])
        self.assertEqual(response.context["filter_form"].cleaned_data["sort"], "important")
        self.assertContains(response, "Pendiente de evaluación")
        self.assertNotContains(response, "Más relevante")

    def test_search_keeps_source_language_preferences_and_retention(self):
        expected = self.article("Robots en las empresas")
        self.article("Robots at work", language="en")
        self.article("Robots antiguos", age=15)
        other_topic = self.article("Robots de otro tema")
        other_topic.categories.set([self.other_category])
        source = Source.objects.create(name="Otra fuente buscable")
        other_feed = Feed.objects.create(source=source, name="RSS", url="https://example.com/other-search", is_active=True)
        other_source = self.article("Robots de otra fuente")
        other_source.feed = other_feed
        other_source.save()
        inactive_feed = Feed.objects.create(source=self.source, name="Inactivo", url="https://example.com/inactive-search")
        inactive = self.article("Robots sin actividad")
        inactive.feed = inactive_feed
        inactive.save()
        _, results = self.results("robots", source=self.source.pk, language="es")
        self.assertEqual([item.pk for item in results], [expected.pk])

    def test_pagination_and_save_preserve_query(self):
        UserPreference.objects.get(user=self.user).categories.add(self.other_category)
        for index in range(11):
            article = self.article(f"Robots y mercados edición {index}")
            article.categories.add(self.other_category)
        response, results = self.results("robots mercado", source=self.source.pk, language="es")
        section = response.context
        query = parse_qs(urlsplit(section["next_url"]).query)
        self.assertEqual(query["q"], ["robots mercado"])
        self.assertIn("cursor", query)
        self.assertEqual(query["source"], [str(self.source.pk)])
        self.assertNotContains(response, "article-lead")
        self.assertNotContains(response, "La más reciente")
        next_url = reverse("category_news", args=[self.category.slug]) + "?q=robots+mercado&visible=19"
        response = self.client.post(reverse("save_article", args=[results[0].pk]), {"next": next_url})
        self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_title_and_language_updates_are_searchable_immediately(self):
        article = self.article("Empresas investigan robots")
        self.assertTrue(search_articles(Article.objects.all(), "empresa").exists())
        Article.objects.filter(pk=article.pk).update(title="Researchers explore planets", language="en")
        self.assertFalse(search_articles(Article.objects.all(), "empresa").exists())
        self.assertTrue(search_articles(Article.objects.all(), "researcher").exists())

    def test_cursor_keeps_relevance_and_date_order_across_batches(self):
        import re
        for index in range(31):
            self.article("Robots y mercados" if index % 2 else "Robots estudian las oportunidades y los mercados", age=index % 4)
        expected = list(search_articles(Article.objects.all(), "robots mercado").order_by("-relevance", "-published_at", "-id").values_list("id", flat=True))
        first, rows = self.results("robots mercado")
        actual = [row.pk for row in rows]
        url = first.context["next_url"]
        for _ in range(5):
            if not url:
                break
            response = self.client.get(url, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            actual.extend(map(int, re.findall(r'data-article-id="(\d+)"', data["html"])))
            url = data["next_url"]
        self.assertEqual(actual, expected)

    def test_query_length_limit_and_html_escaping(self):
        self.article("Robots investigan planetas")
        response, results = self.results("x" * 201)
        self.assertTrue(response.context["filter_form"].errors)
        self.assertEqual(results, [])
        response, _ = self.results("<script>alert(1)</script>")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_search_index_is_used_for_selective_queries(self):
        Article.objects.bulk_create([
            Article(feed=self.feed, title="Noticias generales del día", language="es", original_url=f"https://example.com/index-{index}")
            for index in range(2000)
        ])
        self.article("Un descubrimiento de superconductividad")
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE news_article")
        plan = search_articles(Article.objects.all(), "superconductividad").explain()
        self.assertIn("article_title_search_gin", plan)


class SearchFormTests(TestCase):
    def test_search_input_and_overlong_query(self):
        user = get_user_model().objects.create_user(username="formulario-buscador")
        category = Category.objects.create(name="Prueba formulario", slug="formulario-buscador")
        preference = UserPreference.objects.create(user=user)
        preference.categories.add(category)
        self.client.force_login(user)
        response = self.client.get(reverse("category_news", args=[category.slug]))
        self.assertContains(response, 'type="search"')
        self.assertContains(response, "Buscar en títulos")
        if connection.vendor != "postgresql":
            response = self.client.get(reverse("category_news", args=[category.slug]), {"q": "empresa"})
            self.assertContains(response, "La búsqueda no está disponible en este entorno.")
            self.assertEqual(response.context["articles"], [])
        response = self.client.get(reverse("category_news", args=[category.slug]), {"q": "x" * 201})
        self.assertTrue(response.context["filter_form"].errors)
        self.assertEqual(response.context["articles"], [])


class SavedArticleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="guardador")
        self.other_user = get_user_model().objects.create_user(username="otro-lector")
        self.category = Category.objects.create(name="Tema guardado", slug="tema-guardado")
        preference = UserPreference.objects.create(user=self.user)
        preference.categories.add(self.category)
        source = Source.objects.create(name="Fuente de guardadas")
        self.feed = Feed.objects.create(source=source, name="RSS", url="https://example.com/saved-rss", is_active=True)
        self.article = Article.objects.create(
            feed=self.feed, title="Noticia para guardar", original_url="https://example.com/saved",
            published_at=timezone.now(), language="es",
        )
        self.article.categories.add(self.category)
        self.client.force_login(self.user)
        self.save_url = reverse("save_article", args=[self.article.pk])
        self.remove_url = reverse("remove_saved_article", args=[self.article.pk])

    def test_requires_login_post_and_csrf(self):
        for url in (self.save_url, self.remove_url):
            self.assertEqual(self.client.get(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        for url in (self.save_url, self.remove_url):
            self.assertEqual(csrf_client.post(url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("saved_articles")).status_code, 302)
        for url in (self.save_url, self.remove_url):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(SavedArticle.objects.exists())

    def test_save_is_idempotent_and_keeps_page_and_filters(self):
        next_url = reverse("category_news", args=[self.category.slug]) + "?language=es&visible=19"
        for _ in range(2):
            response = self.client.post(self.save_url, {"next": next_url})
            self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertEqual(SavedArticle.objects.filter(user=self.user, article=self.article).count(), 1)
        response = self.client.get(reverse("category_news", args=[self.category.slug]))
        self.assertContains(response, "Quitar de guardadas")
        response = self.client.get(reverse("saved_articles"))
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.article.original_url)
        self.assertContains(response, "Fuente de guardadas")

    def test_users_only_see_and_remove_their_own_saves(self):
        SavedArticle.objects.create(user=self.other_user, article=self.article)
        response = self.client.get(reverse("saved_articles"))
        self.assertNotContains(response, self.article.title)
        self.client.post(self.remove_url)
        self.assertTrue(SavedArticle.objects.filter(user=self.other_user).exists())
        self.client.post(self.save_url)
        self.client.post(self.remove_url)
        self.client.post(self.remove_url)
        self.assertFalse(SavedArticle.objects.filter(user=self.user).exists())
        self.assertTrue(SavedArticle.objects.filter(user=self.other_user).exists())

    def test_external_redirects_are_rejected(self):
        for url in (self.save_url, self.remove_url):
            for next_url in ("https://example.com/", "//example.com/", "javascript:alert(1)"):
                response = self.client.post(url, {"next": next_url})
                self.assertRedirects(response, reverse("saved_articles"))

    def test_missing_old_or_inactive_articles_cannot_be_saved(self):
        self.assertEqual(self.client.post(reverse("save_article", args=[999999])).status_code, 404)
        self.feed.is_active = False
        self.feed.save()
        self.assertEqual(self.client.post(self.save_url).status_code, 404)
        self.feed.is_active = True
        self.feed.save()
        Article.objects.filter(pk=self.article.pk).update(published_at=timezone.now() - timedelta(days=15))
        self.assertEqual(self.client.post(self.save_url).status_code, 404)
        self.assertFalse(SavedArticle.objects.exists())

    def test_saved_list_ignores_preferences_and_expires_with_article(self):
        SavedArticle.objects.create(user=self.user, article=self.article)
        UserPreference.objects.get(user=self.user).categories.clear()
        self.feed.is_active = False
        self.feed.save()
        self.assertContains(self.client.get(reverse("saved_articles")), self.article.title)
        Article.objects.filter(pk=self.article.pk).update(published_at=timezone.now() - timedelta(days=15))
        self.assertNotContains(self.client.get(reverse("saved_articles")), self.article.title)
        call_command("purge_old_articles", stdout=StringIO())
        self.assertFalse(SavedArticle.objects.exists())

    def test_saved_list_paginates_in_save_order(self):
        for index in range(11):
            article = Article.objects.create(
                feed=self.feed, title=f"Guardada {index}", original_url=f"https://example.com/saved-{index}",
                published_at=timezone.now(),
            )
            SavedArticle.objects.create(user=self.user, article=article)
        response = self.client.get(reverse("saved_articles"))
        self.assertEqual(len(response.context["page"]), 10)
        self.assertEqual(response.context["page"][0].article.title, "Guardada 10")
        response = self.client.get(reverse("saved_articles"), {"page": 2})
        self.assertEqual(len(response.context["page"]), 1)
        self.assertContains(response, "Guardada 0")
        self.assertContains(response, 'name="next" value="/guardadas/?page=2"')
        self.assertEqual(self.client.get(reverse("saved_articles"), {"page": "abc"}).status_code, 200)

    def test_empty_messages_offer_next_actions(self):
        self.assertContains(self.client.get(reverse("saved_articles")), "Todavía no tenés noticias guardadas")
        other_source = Source.objects.create(name="Otra fuente de guardadas")
        other_feed = Feed.objects.create(source=other_source, name="RSS", url="https://example.com/other-saved-rss", is_active=True)
        other_article = Article.objects.create(
            feed=other_feed, title="Noticia en inglés", original_url="https://example.com/english-saved",
            published_at=timezone.now(), language="en",
        )
        other_article.categories.add(self.category)
        response = self.client.get(reverse("category_news", args=[self.category.slug]), {"source": self.feed.source_id, "language": "en"})
        self.assertContains(response, "No hay noticias con estos filtros")
        self.assertContains(response, "Limpiar filtros")
        response = self.client.get(reverse("category_news", args=[self.category.slug]), {"source": "abc"})
        self.assertContains(response, "Revisá los filtros")
        Article.objects.all().delete()
        self.assertContains(self.client.get(reverse("category_news", args=[self.category.slug])), "Todavía no hay noticias recientes de esta categoría")
        UserPreference.objects.get(user=self.user).categories.clear()
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, "Elegí tus categorías")
        self.assertContains(response, "Elegir categorías")


class IngestionOriginTests(TestCase):
    def setUp(self):
        source = Source.objects.create(name="Fuente sintética de orígenes")
        self.feed_a = Feed.objects.create(source=source, name="A", url="https://example.com/a")
        self.feed_b = Feed.objects.create(source=source, name="B", url="https://example.com/b")

    def ingest(self, feed, tag, *, guid="", url="https://example.com/article"):
        entry = {
            "title": "Noticia sintética", "link": url, "id": guid,
            "published_parsed": timezone.now().utctimetuple(),
            "tags": [{"term": tag}],
        }
        with patch("news.ingestion.download_feed", return_value=([entry], "", "")):
            return ingest_feed(feed, force_download=True)

    def test_shared_url_combines_categories_and_preserves_attribution(self):
        self.ingest(self.feed_a, "Tecnología", guid="a")
        result = self.ingest(self.feed_b, "Ciencia", guid="b")
        article = Article.objects.get(original_url="https://example.com/article")
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(article.feed_id, self.feed_a.pk)
        self.assertEqual(article.guid, "a")
        self.assertEqual(article.origins.count(), 2)
        self.assertCountEqual(article.categories.values_list("slug", flat=True), ["tecnologia", "ciencia"])

    def test_canonical_url_combines_entries_with_tracking_parameters(self):
        self.ingest(self.feed_a, "Tecnología")
        result = self.ingest(self.feed_b, "Ciencia", url="https://example.com/article?utm_source=test#section")
        self.assertEqual(result.duplicates, 1)
        article = Article.objects.get(original_url="https://example.com/article")
        self.assertEqual(article.origins.count(), 2)
        self.assertCountEqual(article.categories.values_list("slug", flat=True), ["tecnologia", "ciencia"])

    def test_refresh_removes_only_this_origins_categories_and_is_idempotent(self):
        self.ingest(self.feed_a, "Tecnología")
        self.ingest(self.feed_b, "Ciencia")
        self.ingest(self.feed_a, "Etiqueta desconocida")
        self.ingest(self.feed_b, "Ciencia")
        article = Article.objects.get(original_url="https://example.com/article")
        self.assertEqual(list(article.categories.values_list("slug", flat=True)), ["ciencia"])
        self.assertEqual(article.origins.count(), 2)
        self.assertEqual(Article.objects.filter(feed=self.feed_a).count(), 1)
        self.assertEqual(ArticleOrigin.categories.through.objects.filter(articleorigin__article=article).count(), 1)

    def test_secondary_guid_identifies_article_after_link_changes(self):
        self.ingest(self.feed_a, "Tecnología", guid="a")
        self.ingest(self.feed_b, "Ciencia", guid="b")
        result = self.ingest(self.feed_b, "Ciencia", guid="b", url="https://example.com/updated")
        self.assertEqual(result.duplicates, 1)
        self.assertFalse(Article.objects.filter(original_url="https://example.com/updated").exists())
        self.assertEqual(ArticleOrigin.objects.filter(feed=self.feed_b, guid="b").count(), 1)

    def test_guid_is_scoped_to_feed_and_empty_guids_are_allowed(self):
        self.ingest(self.feed_a, "Tecnología", guid="same", url="https://example.com/one")
        result = self.ingest(self.feed_b, "Ciencia", guid="same", url="https://example.com/two")
        self.assertEqual(result.created, 1)
        self.assertEqual(ArticleOrigin.objects.filter(guid="same").count(), 2)
        self.ingest(self.feed_a, "Tecnología", url="https://example.com/no-guid-1")
        self.ingest(self.feed_a, "Tecnología", url="https://example.com/no-guid-2")
        self.assertEqual(ArticleOrigin.objects.filter(feed=self.feed_a, guid="").count(), 2)

    def test_missing_guid_does_not_erase_secondary_identifier(self):
        self.ingest(self.feed_a, "Tecnología")
        self.ingest(self.feed_b, "Ciencia", guid="b")
        self.ingest(self.feed_b, "Ciencia")
        self.assertEqual(ArticleOrigin.objects.get(feed=self.feed_b).guid, "b")

    def test_origin_constraints_reject_duplicate_feed_and_guid(self):
        self.ingest(self.feed_a, "Tecnología", guid="a")
        self.ingest(self.feed_a, "Ciencia", url="https://example.com/other")
        first = Article.objects.get(original_url="https://example.com/article")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ArticleOrigin.objects.create(article=first, feed=self.feed_a)
        other = Article.objects.get(original_url="https://example.com/other")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ArticleOrigin.objects.filter(article=other, feed=self.feed_a).update(guid="a")

    def test_admin_created_article_preserves_primary_categories(self):
        article = Article.objects.create(
            feed=self.feed_a, title="Noticia sintética", original_url="https://example.com/article",
            published_at=timezone.now(),
        )
        article.categories.add(Category.objects.get(slug="tecnologia"))
        self.ingest(self.feed_b, "Ciencia")
        self.assertCountEqual(article.categories.values_list("slug", flat=True), ["tecnologia", "ciencia"])

    def test_cleanup_removes_origins_and_their_category_relations(self):
        self.ingest(self.feed_a, "Tecnología")
        self.ingest(self.feed_b, "Ciencia")
        article = Article.objects.get(original_url="https://example.com/article")
        origin_ids = list(article.origins.values_list("pk", flat=True))
        Article.objects.filter(pk=article.pk).update(published_at=timezone.now() - timedelta(days=15))
        call_command("purge_old_articles", stdout=StringIO())
        self.assertFalse(ArticleOrigin.objects.filter(pk__in=origin_ids).exists())
        self.assertFalse(ArticleOrigin.categories.through.objects.filter(articleorigin_id__in=origin_ids).exists())


class ArticleImageTests(TestCase):
    def setUp(self):
        source = Source.objects.create(name="Medio con imágenes")
        self.feed = Feed.objects.create(source=source, name="RSS", url="https://example.com/image-feed", show_images=True)
        self.entry = {
            "title": "Noticia de imagen", "link": "https://example.com/image-article", "id": "image-1",
            "published_parsed": timezone.now().utctimetuple(),
            "media_content": [{"url": "https://example.com/photo.jpg", "type": "image/jpeg"}],
            "media_credit": [{"content": "<b>Fotógrafa</b>"}],
        }

    def test_media_thumbnail_and_enclosures_respect_permission(self):
        for field in ("media_content", "media_thumbnail", "enclosures"):
            entry = {field: [{"url": "https://example.com/photo.webp", "type": "image/webp"}]}
            self.assertEqual(permitted_image(entry, self.feed), ("https://example.com/photo.webp", self.feed.source.name))
        for entry in ({"media_thumbnail": [{"url": "https://example.com/image/123"}]},
                      {"media_content": [{"url": "https://example.com/image/123", "medium": "image"}]}):
            self.assertEqual(permitted_image(entry, self.feed)[0], "https://example.com/image/123")
        self.feed.show_images = False
        self.assertEqual(permitted_image(self.entry, self.feed), ("", ""))

    def test_non_images_and_unsafe_urls_are_rejected(self):
        for url, kind in (("javascript:alert(1)", "image/jpeg"), ("file:///image.jpg", "image/jpeg"),
                          ("https://example.com/video.mp4", "video/mp4"), ("https://example.com/unknown", "")):
            self.assertEqual(permitted_image({"media_content": [{"url": url, "type": kind}]}, self.feed), ("", ""))

    def test_ingestion_adds_updates_and_revokes_existing_images(self):
        with patch("news.ingestion.download_feed", return_value=([self.entry], "", "")):
            ingest_feed(self.feed)
            article = Article.objects.get(original_url=self.entry["link"])
            self.assertEqual((article.image_url, article.image_credit), ("https://example.com/photo.jpg", "Fotógrafa"))
            self.entry["media_content"][0]["url"] = "https://example.com/replacement.jpg"
            ingest_feed(self.feed, force_download=True)
            article.refresh_from_db()
            self.assertEqual(article.image_url, "https://example.com/replacement.jpg")
            self.feed.show_images = False
            ingest_feed(self.feed, force_download=True)
            article.refresh_from_db()
            self.assertEqual((article.image_url, article.image_credit), ("", ""))

    def test_secondary_origin_does_not_replace_primary_photo_or_credit(self):
        with patch("news.ingestion.download_feed", return_value=([self.entry], "", "")):
            ingest_feed(self.feed)
            secondary = Feed.objects.create(source=self.feed.source, name="Otro RSS", url="https://example.com/secondary", show_images=True)
            self.entry["media_content"][0]["url"] = "https://example.com/other.jpg"
            ingest_feed(secondary)
        article = Article.objects.get(original_url=self.entry["link"])
        self.assertEqual(article.image_url, "https://example.com/photo.jpg")

    def test_forced_download_bypasses_304_to_complete_existing_photo(self):
        article = Article.objects.create(feed=self.feed, title=self.entry["title"],
            original_url=self.entry["link"], published_at=timezone.now())
        self.feed.etag, self.feed.last_modified = "old-tag", "old-date"
        with patch("news.ingestion.urlopen", side_effect=HTTPError(self.feed.url, 304, "Not Modified", {}, None)):
            self.assertTrue(ingest_feed(self.feed).unchanged)
        article.refresh_from_db()
        self.assertEqual(article.image_url, "")
        with patch("news.ingestion.urlopen") as download, patch("news.ingestion.feedparser.parse") as parse:
            download.return_value.__enter__.return_value.read.return_value = b"<rss/>"
            download.return_value.__enter__.return_value.headers = {}
            parse.return_value = SimpleNamespace(bozo=False, version="rss20", entries=[self.entry])
            result = ingest_feed(self.feed, force_download=True)
            self.assertFalse(any(key.lower().startswith("if-") for key in download.call_args.args[0].headers))
        article.refresh_from_db()
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(article.image_url, "https://example.com/photo.jpg")


class RetentionTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.cutoff = self.now - timedelta(days=14)
        self.source = Source.objects.create(name="Fuente de retención")
        self.feed = Feed.objects.create(
            source=self.source, name="RSS", url="https://example.com/retention", is_active=True,
        )

    def article(self, name, published_at):
        return Article.objects.create(
            feed=self.feed, title=name, original_url=f"https://example.com/{name}",
            published_at=published_at,
        )

    def test_deletes_only_older_articles_including_inactive_feeds(self):
        old = self.article("antigua", self.cutoff - timedelta(seconds=1))
        boundary = self.article("limite", self.cutoff)
        recent = self.article("reciente", self.now)
        self.feed.is_active = False
        self.feed.save()
        category = Category.objects.create(name="Retención", slug="retencion")
        old.categories.add(category)
        output = StringIO()
        with patch("news.retention.timezone.now", return_value=self.now):
            call_command("purge_old_articles", stdout=output)
        self.assertFalse(Article.objects.filter(pk=old.pk).exists())
        self.assertCountEqual(Article.objects.values_list("pk", flat=True), [boundary.pk, recent.pk])
        self.assertTrue(Feed.objects.filter(pk=self.feed.pk).exists())
        self.assertTrue(Source.objects.filter(pk=self.source.pk).exists())
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertIn("Se eliminaron 1 noticias", output.getvalue())

    def test_dry_run_does_not_delete_and_cleanup_is_idempotent(self):
        old = self.article("antigua", self.cutoff - timedelta(days=1))
        output = StringIO()
        call_command("purge_old_articles", dry_run=True, stdout=output)
        self.assertIn("Se eliminarían 1 noticias", output.getvalue())
        self.assertTrue(Article.objects.filter(pk=old.pk).exists())
        call_command("purge_old_articles", stdout=StringIO())
        output = StringIO()
        call_command("purge_old_articles", stdout=output)
        self.assertIn("Se eliminaron 0 noticias", output.getvalue())

    def test_missing_publication_date_uses_capture_date(self):
        old = self.article("sin-fecha-antigua", None)
        recent = self.article("sin-fecha-reciente", None)
        Article.objects.filter(pk=old.pk).update(fetched_at=self.cutoff - timedelta(days=1))
        call_command("purge_old_articles", stdout=StringIO())
        self.assertFalse(Article.objects.filter(pk=old.pk).exists())
        self.assertTrue(Article.objects.filter(pk=recent.pk).exists())

    @patch("news.ingestion.download_feed")
    def test_ingestion_still_rejects_old_entries(self, download):
        download.return_value = ([{
            "title": "Antigua", "link": "https://example.com/old-rss",
            "published_parsed": (self.cutoff - timedelta(days=1)).utctimetuple(),
        }], "", "")
        result = ingest_feed(self.feed)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.created, 0)
        self.assertFalse(Article.objects.filter(feed=self.feed).exists())


class ArticleOriginMigrationTests(TransactionTestCase):
    def test_existing_articles_keep_metadata_and_categories_after_migration(self):
        old_target = [("news", "0006_argentina_markets")]
        new_target = [("news", "0007_article_origins")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            OldSource = old_apps.get_model("news", "Source")
            OldFeed = old_apps.get_model("news", "Feed")
            OldArticle = old_apps.get_model("news", "Article")
            OldCategory = old_apps.get_model("news", "Category")
            source = OldSource.objects.create(name="Fuente sintética de migración")
            feed = OldFeed.objects.create(source=source, name="RSS", url="https://example.com/migration")
            article = OldArticle.objects.create(
                feed=feed, guid="synthetic-guid", title="Título sintético",
                original_url="https://example.com/legacy", canonical_url="https://example.com/legacy",
                fingerprint="a" * 64, language="es", summary="Resumen sintético",
                published_at=timezone.now(),
            )
            category, _ = OldCategory.objects.get_or_create(slug="ciencia", defaults={"name": "Ciencia"})
            article.categories.add(category)
            columns = ["id", "feed_id", "guid", "title", "original_url", "canonical_url",
                       "fingerprint", "language", "summary", "published_at", "fetched_at"]
            before = OldArticle.objects.filter(pk=article.pk).values(*columns).get()
            without_guid = OldArticle.objects.create(
                feed=feed, title="Sin GUID", original_url="https://example.com/legacy-no-guid",
            )

            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            new_apps = executor.loader.project_state(new_target).apps
            NewArticle = new_apps.get_model("news", "Article")
            NewOrigin = new_apps.get_model("news", "ArticleOrigin")
            self.assertEqual(NewArticle.objects.filter(pk=article.pk).values(*columns).get(), before)
            self.assertEqual(list(NewArticle.objects.get(pk=article.pk).categories.values_list("pk", flat=True)), [category.pk])
            origin = NewOrigin.objects.get(article_id=article.pk)
            self.assertEqual((origin.feed_id, origin.guid), (feed.pk, "synthetic-guid"))
            self.assertEqual(list(origin.categories.values_list("pk", flat=True)), [category.pk])
            self.assertEqual(NewOrigin.objects.get(article_id=without_guid.pk).guid, "")
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())


@skipUnless(connection.vendor == "postgresql", "El índice GIN requiere PostgreSQL")
class ArticleSearchMigrationTests(TransactionTestCase):
    def test_index_supports_existing_articles_and_can_be_reversed(self):
        old_target = [("news", "0008_savedarticle")]
        new_target = [("news", "0009_article_article_title_search_gin")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            source = old_apps.get_model("news", "Source").objects.create(name="Fuente anterior al índice")
            feed = old_apps.get_model("news", "Feed").objects.create(
                source=source, name="RSS", url="https://example.com/before-index", is_active=True,
            )
            article = old_apps.get_model("news", "Article").objects.create(
                feed=feed, title="Las empresas investigan mercados", language="es",
                original_url="https://example.com/before-index-article", published_at=timezone.now(),
            )
            OldArticle = old_apps.get_model("news", "Article")
            before = OldArticle.objects.filter(pk=article.pk).values().get()
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            NewArticle = executor.loader.project_state(new_target).apps.get_model("news", "Article")
            self.assertEqual(NewArticle.objects.filter(pk=article.pk).values().get(), before)
            self.assertEqual(search_articles(NewArticle.objects.all(), "la empresa").get().pk, article.pk)
            with connection.cursor() as cursor:
                cursor.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'article_title_search_gin'")
                self.assertIn("USING gin", cursor.fetchone()[0])
            MigrationExecutor(connection).migrate(old_target)
            self.assertEqual(OldArticle.objects.filter(pk=article.pk).values().get(), before)
            with connection.cursor() as cursor:
                cursor.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'article_title_search_gin'")
                self.assertIsNone(cursor.fetchone())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())


class ArticleImageMigrationTests(TransactionTestCase):
    def test_existing_metadata_and_default_permissions_survive_migration(self):
        old_target = [("news", "0012_feed_allow_ai_briefing")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            apps = executor.loader.project_state(old_target).apps
            source = apps.get_model("news", "Source").objects.create(name="Medio anterior a imágenes")
            apps.get_model("news", "Feed").objects.get_or_create(
                url="https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
                defaults={"source": source, "name": "MIT RSS"},
            )
            feed = apps.get_model("news", "Feed").objects.create(source=source, name="RSS", url="https://example.com/old-images")
            old_article = apps.get_model("news", "Article")
            article = old_article.objects.create(feed=feed, title="Titular existente", original_url="https://example.com/old-image-article", published_at=timezone.now())
            before = old_article.objects.filter(pk=article.pk).values().get()
            executor = MigrationExecutor(connection)
            target = [("news", "0014_enable_mit_images")]
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            migrated = current.get_model("news", "Article").objects.get(pk=article.pk)
            self.assertEqual((migrated.image_url, migrated.image_credit), ("", ""))
            self.assertEqual(current.get_model("news", "Article").objects.filter(pk=article.pk).values(*before).get(), before)
            self.assertFalse(current.get_model("news", "Feed").objects.get(pk=feed.pk).show_images)
            self.assertEqual(list(current.get_model("news", "Feed").objects.filter(show_images=True).values_list("url", flat=True)), ["https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"])
            MigrationExecutor(connection).migrate(old_target)
            self.assertEqual(old_article.objects.filter(pk=article.pk).values().get(), before)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
