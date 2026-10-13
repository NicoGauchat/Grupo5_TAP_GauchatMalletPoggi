from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Case, F, Q, When


LANGUAGES = [("es", "spanish"), ("en", "english"), ("pt", "portuguese")]


def language_filter(code):
    return Q(language__iexact=code) | Q(language__istartswith=code + "-") | Q(language__istartswith=code + "_")


def title_vector():
    return Case(
        *[When(language_filter(code), then=SearchVector("title", config=config)) for code, config in LANGUAGES],
        default=SearchVector("title", config="simple"),
    )


def search_articles(articles, text):
    matches = Q()
    known_languages = Q()
    ranks = []
    for code, config in LANGUAGES:
        language = language_filter(code)
        query = SearchQuery(text, config=config)
        matches |= language & Q(search_vector=query)
        known_languages |= language
        ranks.append(When(language, then=SearchRank(F("search_vector"), query, cover_density=True, normalization=2)))
    query = SearchQuery(text, config="simple")
    matches |= ~known_languages & Q(search_vector=query)
    return articles.annotate(
        search_vector=title_vector(),
        relevance=Case(*ranks, default=SearchRank(F("search_vector"), query, cover_density=True, normalization=2)),
    ).filter(matches)
