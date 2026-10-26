from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0018_expand_categories_and_sources")]

    operations = [
        migrations.AddField(
            model_name="story", name="grouping_version",
            field=models.PositiveSmallIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="story", name="grouping_version",
            field=models.PositiveSmallIntegerField(default=1, editable=False),
        ),
    ]
