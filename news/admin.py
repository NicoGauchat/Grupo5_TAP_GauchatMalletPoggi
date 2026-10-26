from django.contrib import admin

from .models import Article, Category, Feed, NewsBriefing, Source, Story, UserPreference


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url", "license_url")
    search_fields = ("name",)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "language", "is_active", "show_summary", "show_images", "allow_ai_briefing", "allow_ai_grouping")
    list_filter = ("is_active", "show_summary", "show_images", "allow_ai_briefing", "allow_ai_grouping", "source")
    filter_horizontal = ("categories",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "feed", "published_at", "fetched_at", "llm_classified_at")
    list_filter = ("feed__source",)
    search_fields = ("title", "original_url")
    filter_horizontal = ("categories", "llm_categories")
    raw_id_fields = ("story",)

    def save_model(self, request, obj, form, change):
        previous = Article.objects.filter(pk=obj.pk).values_list("story_id", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if "story" in form.changed_data or "title" in form.changed_data:
            Story.objects.filter(pk__in=[pk for pk in (previous, obj.story_id) if pk]).update(importance_scored_at=None)


class StoryArticleInline(admin.TabularInline):
    model = Article
    fields = ("title", "feed", "published_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "llm_model", "grouping_version", "importance_score", "importance_scored_at")
    list_filter = ("grouping_version", "importance_score")
    search_fields = ("articles__title",)
    readonly_fields = ("created_at", "llm_model", "grouping_version", "importance_score", "importance_reason", "importance_scored_at", "importance_model")
    inlines = (StoryArticleInline,)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "classification_mode")
    filter_horizontal = ("categories",)


@admin.register(NewsBriefing)
class NewsBriefingAdmin(admin.ModelAdmin):
    list_display = ("generated_at", "window_start", "article_count", "status", "error_code")
    readonly_fields = list_display
    list_filter = ("status", "error_code")
