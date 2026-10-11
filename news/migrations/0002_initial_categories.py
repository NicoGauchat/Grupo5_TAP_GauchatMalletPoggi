from django.db import migrations


INITIAL_CATEGORIES = [
    ("Tecnología", "tecnologia"),
    ("Inteligencia artificial", "inteligencia-artificial"),
    ("Ciencia", "ciencia"),
    ("Economía", "economia"),
    ("Geopolítica", "geopolitica"),
]


def create_categories(apps, schema_editor):
    Category = apps.get_model("news", "Category")
    for name, slug in INITIAL_CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("news", "0001_initial")]

    operations = [migrations.RunPython(create_categories, migrations.RunPython.noop)]
