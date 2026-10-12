from django.db import migrations


def add_categories_and_market_feed(apps, schema_editor):
    Category = apps.get_model("news", "Category")
    Source = apps.get_model("news", "Source")
    Feed = apps.get_model("news", "Feed")

    argentina, _ = Category.objects.get_or_create(
        slug="argentina", defaults={"name": "Argentina"}
    )
    markets, _ = Category.objects.get_or_create(
        slug="mercados-finanzas", defaults={"name": "Mercados y finanzas"}
    )
    politics = Feed.objects.get(url="https://www.clarin.com/rss/politica/")
    politics.categories.add(argentina)

    source, _ = Source.objects.get_or_create(
        name="Cinco Días",
        defaults={"website_url": "https://cincodias.elpais.com/"},
    )
    feed, _ = Feed.objects.get_or_create(
        url="https://feeds.elpais.com/mrss-s/list/ep/site/cincodias.elpais.com/section/mercados-financieros",
        defaults={
            "source": source,
            "name": "Mercados",
            "language": "es",
            "is_active": True,
            "show_summary": False,
        },
    )
    feed.categories.add(markets)

    los_andes, _ = Source.objects.get_or_create(
        name="Los Andes", defaults={"website_url": "https://www.losandes.com.ar/"}
    )
    for name, url, categories in [
        (
            "Política",
            "https://www.losandes.com.ar/rss/pages/politica.xml",
            ("politica-argentina", "argentina"),
        ),
        (
            "Economía",
            "https://www.losandes.com.ar/rss/pages/economia.xml",
            ("economia", "argentina"),
        ),
    ]:
        local_feed, _ = Feed.objects.get_or_create(
            url=url,
            defaults={
                "source": los_andes,
                "name": name,
                "language": "es",
                "is_active": True,
                "show_summary": False,
            },
        )
        local_feed.categories.add(*Category.objects.filter(slug__in=categories))


class Migration(migrations.Migration):
    dependencies = [("news", "0005_expand_news_sources")]

    operations = [migrations.RunPython(add_categories_and_market_feed, migrations.RunPython.noop)]
