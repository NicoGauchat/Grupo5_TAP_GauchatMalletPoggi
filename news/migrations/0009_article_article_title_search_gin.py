import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models


class PostgreSQLIndex(migrations.AddIndex):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0008_savedarticle'),
    ]

    operations = [
        PostgreSQLIndex(
            model_name='article',
            index=django.contrib.postgres.indexes.GinIndex(models.Case(models.When(models.Q(('language__iexact', 'es'), ('language__istartswith', 'es-'), ('language__istartswith', 'es_'), _connector='OR'), then=django.contrib.postgres.search.SearchVector('title', config='spanish')), models.When(models.Q(('language__iexact', 'en'), ('language__istartswith', 'en-'), ('language__istartswith', 'en_'), _connector='OR'), then=django.contrib.postgres.search.SearchVector('title', config='english')), models.When(models.Q(('language__iexact', 'pt'), ('language__istartswith', 'pt-'), ('language__istartswith', 'pt_'), _connector='OR'), then=django.contrib.postgres.search.SearchVector('title', config='portuguese')), default=django.contrib.postgres.search.SearchVector('title', config='simple')), name='article_title_search_gin'),
        ),
    ]
