from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .ingestion import ingest_feed
from .models import Article, ArticleOrigin, Category, Feed, SavedArticle, Source, UserPreference


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

    def titles(self, response):
        return [article.title for section in response.context["sections"] for article in section["articles"]]

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("news_feed"))
        self.assertRedirects(response, reverse("login") + "?next=/noticias/", fetch_redirect_response=False)

    def test_combines_source_and_language(self):
        self.article("correcta")
        self.article("otro-idioma", language="en")
        self.article("otra-fuente", feed=self.other_feed)
        response = self.client.get(reverse("news_feed"), {"source": self.source.pk, "language": "es"})
        self.assertEqual(self.titles(response), ["correcta"])
        self.assertTrue(response.context["filters_active"])
        self.assertContains(response, f'value="{self.source.pk}" selected')
        self.assertContains(response, 'value="es" selected')
        self.assertContains(response, 'method="get"')

    def test_filters_source_independently(self):
        self.article("espanol")
        self.article("ingles", language="en")
        self.article("otra", feed=self.other_feed)
        response = self.client.get(reverse("news_feed"), {"source": self.source.pk})
        self.assertCountEqual(self.titles(response), ["espanol", "ingles"])

    def test_filters_language_independently(self):
        self.article("espanol")
        self.article("ingles-a", language="en")
        self.article("ingles-b", feed=self.other_feed, language="en")
        response = self.client.get(reverse("news_feed"), {"language": "en"})
        self.assertCountEqual(self.titles(response), ["ingles-a", "ingles-b"])

    def test_only_current_users_categories_active_feeds_and_recent_articles(self):
        self.article("visible")
        self.article("otro-tema", category=self.other_category)
        self.article("antigua", age=61)
        self.other_feed.is_active = False
        self.other_feed.save()
        self.article("inactiva", feed=self.other_feed)
        response = self.client.get(reverse("news_feed"))
        self.assertEqual(self.titles(response), ["visible"])
        self.assertQuerySetEqual(response.context["filter_form"].fields["source"].queryset, [self.source])

    def test_invalid_filters_have_errors_and_no_unfiltered_results(self):
        self.article("visible")
        for query in ({"source": "abc"}, {"source": "999999"}, {"language": "zz"}):
            with self.subTest(query=query):
                response = self.client.get(reverse("news_feed"), query)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["filter_form"].errors)
                self.assertEqual(self.titles(response), [])
                self.assertContains(response, "limpiar los filtros")

    def test_empty_combination_and_reset(self):
        self.article("espanol")
        self.article("ingles", feed=self.other_feed, language="en")
        response = self.client.get(reverse("news_feed"), {"source": self.source.pk, "language": "en"})
        self.assertEqual(self.titles(response), [])
        self.assertContains(response, "No hay noticias de esta categoría con los filtros elegidos")
        response = self.client.get(reverse("news_feed"))
        self.assertCountEqual(self.titles(response), ["espanol", "ingles"])

    def test_filter_applies_before_ten_article_limit(self):
        older = self.article("ingles-antigua", language="en", age=10)
        for index in range(11):
            self.article(f"espanol-{index}")
        response = self.client.get(reverse("news_feed"), {"language": "en"})
        self.assertEqual(response.context["sections"][0]["articles"], [older])
        response = self.client.get(reverse("news_feed"))
        articles = response.context["sections"][0]["articles"]
        self.assertEqual(len(articles), 10)
        self.assertNotIn(older, articles)
        self.assertEqual(articles[0].title, "espanol-10")

    def test_multiple_categories_do_not_duplicate_articles_in_a_section(self):
        UserPreference.objects.get(user=self.user).categories.add(self.other_category)
        article = self.article("compartida")
        article.categories.add(self.other_category)
        response = self.client.get(reverse("news_feed"))
        self.assertEqual(len(response.context["sections"]), 2)
        for section in response.context["sections"]:
            self.assertEqual(section["articles"], [article])

    def test_account_without_preferences_has_empty_state(self):
        UserPreference.objects.get(user=self.user).delete()
        response = self.client.get(reverse("news_feed"))
        self.assertContains(response, "Elegí tus categorías")
        self.assertEqual(response.context["sections"], [])

    def test_pagination_boundaries_and_controls(self):
        for count in (0, 10, 11, 23):
            with self.subTest(count=count):
                Article.objects.all().delete()
                for index in range(count):
                    self.article(f"noticia-{index}")
                response = self.client.get(reverse("news_feed"))
                section = response.context["sections"][0]
                self.assertEqual(section["article_count"], count)
                self.assertEqual(len(section["articles"]), min(count, 10))
                self.assertEqual(section["page"].number, 1)
                if count > 10:
                    self.assertContains(response, 'aria-label="Páginas de Tema de prueba"')
                    self.assertContains(response, '<span aria-disabled="true">Anterior</span>', html=True)
                    self.assertIsNotNone(section["next_url"])
                else:
                    self.assertNotContains(response, 'class="category-pagination"')
                    self.assertIsNone(section["next_url"])

    def test_pages_cover_all_articles_in_stable_order_without_duplicates(self):
        for index in range(23):
            article = self.article(f"noticia-{index}")
            article.categories.add(self.other_category)
        # Fuerza el empate de fechas para comprobar el desempate por ID.
        Article.objects.all().update(published_at=timezone.now())
        expected = list(Article.objects.order_by("-id").values_list("id", flat=True))
        actual = []
        for number, count in ((1, 10), (2, 10), (3, 3)):
            response = self.client.get(reverse("news_feed"), {"page_tema-prueba": number})
            section = response.context["sections"][0]
            self.assertEqual(len(section["articles"]), count)
            self.assertEqual(section["article_count"], 23)
            actual.extend(article.pk for article in section["articles"])
            if number == 1:
                self.assertContains(response, "Más reciente")
            else:
                self.assertNotContains(response, "Más reciente")
            if number == 3:
                self.assertIsNone(section["next_url"])
                self.assertContains(response, '<span aria-disabled="true">Siguiente</span>', html=True)
        self.assertEqual(actual, expected)
        self.assertEqual(len(set(actual)), 23)

    def test_pages_are_independent_and_column_order_uses_total_count(self):
        UserPreference.objects.get(user=self.user).categories.add(self.other_category)
        for index in range(23):
            self.article(f"primera-{index}")
        for index in range(11):
            self.article(f"segunda-{index}", category=self.other_category)
        response = self.client.get(reverse("news_feed"), {
            "page_tema-prueba": 3, "page_otro-tema": 2,
        })
        sections = response.context["sections"]
        self.assertEqual([section["category"] for section in sections], [self.category, self.other_category])
        self.assertEqual([len(section["articles"]) for section in sections], [3, 1])
        self.assertEqual([section["page"].number for section in sections], [3, 2])
        self.assertEqual([section["article_count"] for section in sections], [23, 11])

    def test_page_links_preserve_filters_other_pages_and_section_anchor(self):
        UserPreference.objects.get(user=self.user).categories.add(self.other_category)
        for index in range(23):
            article = self.article(f"ingles-{index}", language="en")
            article.categories.add(self.other_category)
        self.article("excluida-por-fuente", language="en", feed=self.other_feed)
        self.article("excluida-por-idioma")
        response = self.client.get(reverse("news_feed"), {
            "source": self.source.pk, "language": "en",
            "page_tema-prueba": 2, "page_otro-tema": 3,
        })
        section = next(s for s in response.context["sections"] if s["category"] == self.category)
        self.assertEqual(section["article_count"], 23)
        for key, number in (("previous_url", "1"), ("next_url", "3")):
            url = urlsplit(section[key])
            self.assertEqual(url.path, reverse("news_feed"))
            self.assertEqual(url.fragment, "category-tema-prueba")
            self.assertEqual(parse_qs(url.query), {
                "source": [str(self.source.pk)], "language": ["en"],
                "page_tema-prueba": [number], "page_otro-tema": ["3"],
            })
        self.assertTrue(all(article.feed_id == self.feed.pk and article.language == "en"
                            for article in section["articles"]))

    def test_invalid_page_numbers_and_pages_removed_by_retention(self):
        for index in range(23):
            self.article(f"noticia-{index}")
        for value, expected in (("", 1), ("abc", 1), ("1.5", 1), ("0", 1), ("-2", 1),
                                ("999999", 3), ("9" * 5000, 1)):
            with self.subTest(value=value[:12]):
                response = self.client.get(reverse("news_feed"), {"page_tema-prueba": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["sections"][0]["page"].number, expected)
        Article.objects.all().update(published_at=timezone.now() - timedelta(days=15))
        response = self.client.get(reverse("news_feed"), {"page_tema-prueba": 3})
        self.assertEqual(response.context["sections"][0]["page"].number, 1)
        self.assertEqual(self.titles(response), [])

    def test_filter_submission_and_reset_restart_pages(self):
        for index in range(23):
            self.article(f"noticia-{index}")
        response = self.client.get(reverse("news_feed"), {"page_tema-prueba": 2})
        self.assertNotContains(response, 'name="page_tema-prueba"')
        self.assertContains(response, f'<a class="filter-reset" href="{reverse("news_feed")}">Limpiar filtros</a>', html=True)
        for query in ({"language": "es"}, {}):
            response = self.client.get(reverse("news_feed"), query)
            self.assertEqual(response.context["sections"][0]["page"].number, 1)

    def test_invalid_filters_with_page_parameters_do_not_expose_articles(self):
        for index in range(23):
            self.article(f"noticia-{index}")
        response = self.client.get(reverse("news_feed"), {"source": "abc", "page_tema-prueba": 2})
        self.assertTrue(response.context["filter_form"].errors)
        self.assertEqual(self.titles(response), [])
        self.assertNotContains(response, 'class="category-pagination"')


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
        next_url = reverse("news_feed") + "?language=es&page_tema-guardado=2"
        for _ in range(2):
            response = self.client.post(self.save_url, {"next": next_url})
            self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertEqual(SavedArticle.objects.filter(user=self.user, article=self.article).count(), 1)
        response = self.client.get(reverse("news_feed"))
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
        response = self.client.get(reverse("news_feed"), {"source": self.feed.source_id, "language": "en"})
        self.assertContains(response, "No hay noticias con estos filtros")
        self.assertContains(response, "Limpiar filtros")
        response = self.client.get(reverse("news_feed"), {"source": "abc"})
        self.assertContains(response, "Revisá los filtros")
        Article.objects.all().delete()
        self.assertContains(self.client.get(reverse("news_feed")), "Todavía no hay noticias disponibles para tus categorías")
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
