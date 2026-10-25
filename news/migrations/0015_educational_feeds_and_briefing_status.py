from django.db import migrations, models


MIT = "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"
FEEDS = [
    MIT,
    *[f"https://www.clarin.com/rss/{section}/" for section in ("tecnologia", "politica", "mundo", "economia")],
    *[f"https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/{section}/portada"
      for section in ("tecnologia", "internacional", "economia")],
    *[f"https://www.losandes.com.ar/rss/pages/{section}.xml" for section in ("politica", "economia")],
    "https://feeds.elpais.com/mrss-s/list/ep/site/cincodias.elpais.com/section/mercados-financieros",
]


def enable_educational_feeds(apps, schema_editor):
    apps.get_model("news", "Feed").objects.filter(url__in=FEEDS).update(
        show_images=True, allow_ai_briefing=True, etag="", last_modified="",
    )
    apps.get_model("news", "NewsBriefing").objects.filter(items__isnull=True).update(status="empty")


def restore_permissions(apps, schema_editor):
    feeds = apps.get_model("news", "Feed").objects.filter(url__in=FEEDS)
    feeds.update(allow_ai_briefing=False, show_images=False)
    feeds.filter(url=MIT).update(show_images=True)


class Migration(migrations.Migration):
    dependencies = [("news", "0014_enable_mit_images")]
    operations = [
        migrations.AddField("newsbriefing", "status", models.CharField(
            max_length=10, default="ready", choices=[("ready", "Generado"), ("empty", "Vacío"), ("error", "Error")],
        )),
        migrations.AddField("newsbriefing", "error_code", models.CharField(max_length=30, blank=True)),
        migrations.AlterField("feed", "show_images", models.BooleanField(
            default=False, help_text="Mostrar fotografías recibidas en el RSS, conservando créditos.",
        )),
        migrations.AlterField("feed", "allow_ai_briefing", models.BooleanField(
            default=False, verbose_name="Permitir en presentación IA",
            help_text="Incluir los titulares de este feed en la síntesis común de las últimas 24 horas.",
        )),
        migrations.RunPython(enable_educational_feeds, restore_permissions),
    ]
