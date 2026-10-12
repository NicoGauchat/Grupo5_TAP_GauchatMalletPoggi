from django.db import migrations


NEW_FEEDS = [
    ("Clarín", "https://www.clarin.com/", "Política", "https://www.clarin.com/rss/politica/", "politica-argentina"),
    ("Clarín", "https://www.clarin.com/", "Mundo", "https://www.clarin.com/rss/mundo/", "geopolitica"),
    ("Clarín", "https://www.clarin.com/", "Economía", "https://www.clarin.com/rss/economia/", "economia"),
    ("EL PAÍS", "https://elpais.com/", "Internacional", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada", "geopolitica"),
    ("EL PAÍS", "https://elpais.com/", "Economía", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada", "economia"),
]


def add_news_sources(apps, schema_editor):
    Category = apps.get_model("news", "Category")
    Source = apps.get_model("news", "Source")
    Feed = apps.get_model("news", "Feed")

    Category.objects.get_or_create(name="Política argentina", defaults={"slug": "politica-argentina"})

    for source_name, website_url, feed_name, feed_url, category_slug in NEW_FEEDS:
        source, _ = Source.objects.get_or_create(
            name=source_name,
            defaults={"website_url": website_url},
        )
        feed, _ = Feed.objects.get_or_create(
            url=feed_url,
            defaults={
                "source": source,
                "name": feed_name,
                "language": "es",
                "is_active": True,
                "show_summary": False,
            },
        )
        feed.categories.add(Category.objects.get(slug=category_slug))


class Migration(migrations.Migration):
    dependencies = [("news", "0004_seed_initial_feeds")]

    operations = [migrations.RunPython(add_news_sources, migrations.RunPython.noop)]
