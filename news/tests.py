from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .ingestion import ingest_feed
from .models import Article, Category, Feed, Source, UserPreference


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
