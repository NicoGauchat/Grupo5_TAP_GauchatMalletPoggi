from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Source(models.Model):
    name = models.CharField(max_length=120, unique=True)
    website_url = models.URLField(max_length=2048, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Feed(models.Model):
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="feeds")
    name = models.CharField(max_length=120)
    url = models.URLField(max_length=2048, unique=True)
    language = models.CharField(max_length=10, blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="feeds")
    is_active = models.BooleanField(default=False)
    show_summary = models.BooleanField(default=False)

    class Meta:
        ordering = ["source__name", "name"]

    def __str__(self):
        return f"{self.source.name} — {self.name}"


class Article(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name="articles")
    categories = models.ManyToManyField(Category, blank=True, related_name="articles")
    guid = models.CharField(max_length=512, blank=True)
    original_url = models.URLField(max_length=2048, unique=True)
    canonical_url = models.URLField(max_length=2048, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)
    language = models.CharField(max_length=10, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["-published_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["feed", "guid"],
                condition=~models.Q(guid=""),
                name="unique_article_guid_per_feed",
            ),
            models.UniqueConstraint(
                fields=["canonical_url"],
                condition=~models.Q(canonical_url=""),
                name="unique_article_canonical_url",
            ),
        ]

    def __str__(self):
        return self.title


class UserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_preference",
    )
    categories = models.ManyToManyField(Category, blank=True, related_name="users")

    def __str__(self):
        return f"Preferencias de {self.user}"
