from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .forms import PreferenceForm
from .models import Article, UserPreference


ARTICLES_PER_CATEGORY = 10


def home(request):
    if request.user.is_authenticated:
        return redirect("news_feed")
    return render(request, "news/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("preferences")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("preferences")

    return render(request, "news/register.html", {"form": form})


@login_required
def preferences(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    form = PreferenceForm(request.POST or None, instance=preference)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tus categorías se guardaron.")
        return redirect("news_feed")

    return render(request, "news/preferences.html", {"form": form})


@login_required
def news_feed(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    sections = []
    for category in preference.categories.all():
        articles = list(
            Article.objects.filter(categories=category, feed__is_active=True)
            .select_related("feed__source")
            .order_by("-published_at", "-id")[:ARTICLES_PER_CATEGORY]
        )
        sections.append({"category": category, "articles": articles})

    return render(request, "news/feed.html", {"sections": sections})
