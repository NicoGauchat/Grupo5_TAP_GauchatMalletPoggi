from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("news", "0019_story_grouping_version")]

    operations = [
        migrations.AddField(
            model_name="newsbriefingitem", name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="briefing_items", to="news.category"),
        ),
        migrations.AddConstraint(
            model_name="newsbriefingitem",
            constraint=models.UniqueConstraint(fields=("briefing", "category"), name="unique_briefing_item_category"),
        ),
    ]
