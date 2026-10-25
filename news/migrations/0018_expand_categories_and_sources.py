from django.db import migrations


CATEGORIES = [("salud", "Salud"), ("medioambiente", "Medioambiente"), ("deportes", "Deportes")]
CATEGORY_NAMES = dict(CATEGORIES, ciencia="Ciencia", tecnologia="Tecnología", geopolitica="Geopolítica", argentina="Argentina", economia="Economía", **{"politica-argentina": "Política argentina"})
FEEDS = [
    ("EL PAÍS", "https://elpais.com/", "es", name,
     f"https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/{section}/portada", slug)
    for name, section, slug in [
        ("Salud y bienestar", "salud-y-bienestar", "salud"),
        ("Clima y medio ambiente", "clima-y-medio-ambiente", "medioambiente"),
        ("Deportes", "deportes", "deportes"), ("Ciencia", "ciencia", "ciencia"),
    ]
] + [("NASA", "https://www.nasa.gov/", "en", "Technology", "https://www.nasa.gov/technology/feed/", "tecnologia")]
FEEDS += [
    ("Perfil", "https://www.perfil.com/", "es", name, f"https://www.perfil.com/feed/{section}", slug)
    for name, section, slug in [
        ("Política", "politica", "politica-argentina"), ("Salud", "salud", "salud"),
        ("Deportes", "deportes", "deportes"), ("Ciencia", "ciencia", "ciencia"),
        ("Economía", "economia", "economia"), ("Tecnología", "tecnologia", "tecnologia"),
    ]
] + [
    ("Clarín", "https://www.clarin.com/", "es", "Deportes", "https://www.clarin.com/rss/deportes/", "deportes"),
    ("Clarín", "https://www.clarin.com/", "es", "Buena Vida", "https://www.clarin.com/rss/buena-vida/", "salud"),
    ("Los Andes", "https://www.losandes.com.ar/", "es", "Sociedad", "https://www.losandes.com.ar/rss/pages/sociedad.xml", "argentina"),
    ("elDiario.es", "https://www.eldiario.es/", "es", "Internacional", "https://www.eldiario.es/rss/internacional/", "geopolitica"),
]


def add_sources(apps, schema_editor):
    Category, Source, Feed = [apps.get_model("news", name) for name in ("Category", "Source", "Feed")]
    for slug, name in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name})
    for source_name, website, language, name, url, slug in FEEDS:
        source, _ = Source.objects.get_or_create(name=source_name, defaults={"website_url": website})
        feed, _ = Feed.objects.get_or_create(url=url, defaults={
            "source": source, "name": name, "language": language, "is_active": True,
            "show_images": False, "show_summary": False, "allow_ai_briefing": False, "allow_ai_grouping": True,
        })
        category, _ = Category.objects.get_or_create(slug=slug, defaults={"name": CATEGORY_NAMES[slug]})
        feed.categories.add(category)
        if source_name == "Perfil" and slug == "politica-argentina":
            argentina, _ = Category.objects.get_or_create(slug="argentina", defaults={"name": "Argentina"})
            feed.categories.add(argentina)
        if source_name == "elDiario.es":
            source.license_url = "https://creativecommons.org/licenses/by-nc/4.0/"
            source.save(update_fields=["license_url"])


def deactivate_sources(apps, schema_editor):
    apps.get_model("news", "Feed").objects.filter(url__in=[item[4] for item in FEEDS]).update(
        is_active=False, allow_ai_grouping=False,
    )


class Migration(migrations.Migration):
    dependencies = [("news", "0017_story_importance_model_story_importance_reason_and_more")]
    operations = [migrations.RunPython(add_sources, deactivate_sources)]
