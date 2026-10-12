from django.db import migrations


INITIAL_FEEDS = [
    {
        "source": "Clarín",
        "website_url": "https://www.clarin.com/",
        "feed_name": "Tecnología",
        "feed_url": "https://www.clarin.com/rss/tecnologia/",
        "language": "es",
        "category": "tecnologia",
    },
    {
        "source": "EL PAÍS",
        "website_url": "https://elpais.com/",
        "feed_name": "Tecnología",
        "feed_url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
        "language": "es",
        "category": "tecnologia",
    },
    {
        "source": "MIT News",
        "website_url": "https://news.mit.edu/",
        "feed_name": "Artificial Intelligence",
        "feed_url": "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
        "language": "en",
        "category": "inteligencia-artificial",
    },
]


def seed_initial_feeds(apps, schema_editor):
    Source = apps.get_model("news", "Source")
    Feed = apps.get_model("news", "Feed")
    Category = apps.get_model("news", "Category")

    for item in INITIAL_FEEDS:
        source, _ = Source.objects.get_or_create(
            name=item["source"],
            defaults={"website_url": item["website_url"]},
        )
        feed, _ = Feed.objects.get_or_create(
            url=item["feed_url"],
            defaults={
                "source": source,
                "name": item["feed_name"],
                "language": item["language"],
                "is_active": True,
                "show_summary": False,
            },
        )
        category = Category.objects.get(slug=item["category"])
        feed.categories.add(category)


class Migration(migrations.Migration):
    dependencies = [("news", "0003_feed_etag_feed_last_modified")]

    operations = [migrations.RunPython(seed_initial_feeds, migrations.RunPython.noop)]
