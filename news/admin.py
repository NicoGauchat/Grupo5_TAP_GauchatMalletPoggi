from django.contrib import admin

from .models import Article, Category, Feed, NewsBriefing, Source, UserPreference


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url")
    search_fields = ("name",)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "language", "is_active", "show_summary", "allow_ai_briefing")
    list_filter = ("is_active", "show_summary", "allow_ai_briefing", "source")
    filter_horizontal = ("categories",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "feed", "published_at", "fetched_at", "llm_classified_at")
    list_filter = ("feed__source",)
    search_fields = ("title", "original_url")
    filter_horizontal = ("categories", "llm_categories")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "classification_mode")
    filter_horizontal = ("categories",)


@admin.register(NewsBriefing)
class NewsBriefingAdmin(admin.ModelAdmin):
    list_display = ("generated_at", "window_start", "article_count")
    readonly_fields = ("generated_at", "window_start", "article_count")
