from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from .search import title_vector


GROUPING_VERSION = 1


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
    license_url = models.URLField(max_length=2048, blank=True)

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
    show_images = models.BooleanField(default=False, help_text="Mostrar fotografías recibidas en el RSS, conservando créditos.")
    allow_ai_briefing = models.BooleanField(
        verbose_name="Permitir en presentación IA",
        default=False,
        help_text=(
            "Incluir los titulares de este feed en la síntesis común de las últimas 24 horas."
        ),
    )
    etag = models.CharField(max_length=255, blank=True)
    last_modified = models.CharField(max_length=255, blank=True)
    allow_ai_grouping = models.BooleanField(
        default=False, verbose_name="Permitir agrupamiento IA",
        help_text="Enviar titulares y metadatos para agrupar coberturas y evaluar su importancia pública.",
    )

    class Meta:
        ordering = ["source__name", "name"]

    def __str__(self):
        return f"{self.source.name} — {self.name}"


class Story(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    llm_model = models.CharField(max_length=80, blank=True)
    grouping_version = models.PositiveSmallIntegerField(default=GROUPING_VERSION, editable=False)
    importance_score = models.PositiveSmallIntegerField(null=True, blank=True)
    importance_reason = models.CharField(max_length=300, blank=True)
    importance_scored_at = models.DateTimeField(null=True, blank=True)
    importance_model = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(importance_score__isnull=True) | models.Q(importance_score__range=(1, 5)),
            name="story_importance_1_to_5",
        )]

    def __str__(self):
        return f"Acontecimiento {self.pk}"


class Article(models.Model):
    story = models.ForeignKey(Story, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name="articles")
    categories = models.ManyToManyField(Category, blank=True, related_name="articles")
    llm_categories = models.ManyToManyField(Category, blank=True, related_name="llm_articles")
    llm_classified_at = models.DateTimeField(null=True, blank=True)
    llm_model = models.CharField(max_length=80, blank=True)
    guid = models.CharField(max_length=512, blank=True)
    original_url = models.URLField(max_length=2048, unique=True)
    canonical_url = models.URLField(max_length=2048, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    title = models.CharField(max_length=500)
    byline = models.CharField(max_length=300, blank=True)
    summary = models.TextField(blank=True)
    image_url = models.URLField(max_length=2048, blank=True)
    image_credit = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=10, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    @property
    def has_verified_story(self):
        return bool(self.story_id and self.feed.allow_ai_grouping
                    and self.story.grouping_version == GROUPING_VERSION)

    class Meta:
        indexes = [
            models.Index(fields=["-published_at"]),
            GinIndex(title_vector(), name="article_title_search_gin"),
        ]
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


class ArticleOrigin(models.Model):
    """Aporte de cada feed a una noticia compartida entre varios feeds."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="origins")
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name="article_origins")
    guid = models.CharField(max_length=512, blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="article_origins")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["article", "feed"], name="unique_article_origin_feed"),
            models.UniqueConstraint(
                fields=["feed", "guid"], condition=~models.Q(guid=""),
                name="unique_origin_guid_per_feed",
            ),
        ]


class SavedArticle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_articles")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "article"], name="unique_saved_article_user"),
        ]


class NewsBriefing(models.Model):
    """Resumen editorial común generado con noticias de una ventana móvil de 24 h."""

    generated_at = models.DateTimeField(auto_now_add=True)
    window_start = models.DateTimeField()
    article_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, default="ready", choices=[
        ("ready", "Generado"), ("empty", "Vacío"), ("error", "Error"),
    ])
    error_code = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-generated_at", "-id"]


class NewsBriefingItem(models.Model):
    briefing = models.ForeignKey(NewsBriefing, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="briefing_items")
    position = models.PositiveSmallIntegerField()
    text = models.TextField()
    articles = models.ManyToManyField(Article, related_name="briefing_items")

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["briefing", "position"], name="unique_briefing_item_position"),
            models.UniqueConstraint(fields=["briefing", "category"], name="unique_briefing_item_category"),
        ]


class UserPreference(models.Model):
    CLASSIFICATION_BOTH = "both"
    CLASSIFICATION_RULES = "rules"
    CLASSIFICATION_AI = "ai"
    CLASSIFICATION_CHOICES = [
        (CLASSIFICATION_BOTH, "Ambas"),
        (CLASSIFICATION_RULES, "Sólo reglas"),
        (CLASSIFICATION_AI, "Sólo IA"),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_preference",
    )
    categories = models.ManyToManyField(Category, blank=True, related_name="users")
    classification_mode = models.CharField(
        max_length=5, choices=CLASSIFICATION_CHOICES, default=CLASSIFICATION_BOTH,
    )

    def __str__(self):
        return f"Preferencias de {self.user}"
