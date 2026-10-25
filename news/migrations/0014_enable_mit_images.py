from django.db import migrations


MIT_FEED = "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"


def enable_images(apps, schema_editor):
    apps.get_model("news", "Feed").objects.filter(url=MIT_FEED).update(show_images=True)


def disable_images(apps, schema_editor):
    apps.get_model("news", "Feed").objects.filter(url=MIT_FEED).update(show_images=False)


class Migration(migrations.Migration):
    dependencies = [("news", "0013_article_image_credit_article_image_url_and_more")]
    operations = [migrations.RunPython(enable_images, disable_images)]
