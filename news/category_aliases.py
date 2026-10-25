"""Etiquetas RSS aceptadas para cada categoría de la aplicación.

Agregar aquí sólo términos observados en feeds revisados. La comparación es
exacta después de normalizar mayúsculas, tildes y espacios.
"""

import unicodedata


CATEGORY_ALIASES = {
    "tecnologia": {"Tecnología", "Computer science and technology"},
    "inteligencia-artificial": {"Inteligencia artificial", "Artificial intelligence"},
    "ciencia": {"Ciencia"},
    "economia": {"Economía", "Econom�a", "Empresas", "Banca", "Mercados", "Empleo"},
    "geopolitica": {"Guerra", "Conflictos", "Conflictos armados", "Conflictos internacionales", "Ataques militares", "OTAN"},
    "politica-argentina": set(),
    "argentina": set(),
    "mercados-finanzas": {"Mercados financieros", "Bolsa", "Finanzas", "Renta variable", "Renta fija"},
    "salud": {"Salud", "Salud pública", "Salud mental", "Medicina", "Enfermedades"},
    "medioambiente": {"Medio ambiente", "Cambio climático", "Biodiversidad", "Contaminación"},
    "deportes": {"Deportes"},
}


# Los Andes etiqueta todas las entradas con el nombre de la sección. Estas
# equivalencias se limitan a cada feed para no tratar una etiqueta genérica
# "Política" de otro medio como política argentina.
FEED_CATEGORY_ALIASES = {
    "https://www.losandes.com.ar/rss/pages/sociedad.xml": {"Sociedad": {"argentina"}},
    "https://www.nasa.gov/technology/feed/": {
        "Technology": {"tecnologia"}, "Technology Research": {"tecnologia"},
        "Science & Research": {"ciencia"}, "Earth Science": {"ciencia", "medioambiente"},
    },
    "https://www.losandes.com.ar/rss/pages/politica.xml": {
        "Pol�tica": {"politica-argentina", "argentina"},
        "Política": {"politica-argentina", "argentina"},
    },
    "https://www.losandes.com.ar/rss/pages/economia.xml": {
        "Econom�a": {"economia", "argentina"},
        "Economía": {"economia", "argentina"},
    },
}


def normalize_category_name(value):
    text = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(without_accents.casefold().split())


ALIASES_TO_SLUGS = {
    normalize_category_name(alias): slug
    for slug, aliases in CATEGORY_ALIASES.items()
    for alias in aliases
}

FEED_ALIASES_TO_SLUGS = {
    url: {normalize_category_name(alias): slugs for alias, slugs in aliases.items()}
    for url, aliases in FEED_CATEGORY_ALIASES.items()
}

CURATED_FEEDS = {"https://www.eldiario.es/rss/internacional/": {"geopolitica"}}


def category_slugs_for_entry(entry, fallback_slugs, feed_url=""):
    """Usa etiquetas del elemento; recurre al feed sólo si no hay etiquetas."""
    tags = entry.get("tags") or []
    if not tags:
        return set(fallback_slugs) | CURATED_FEEDS.get(feed_url, set())

    slugs = set(CURATED_FEEDS.get(feed_url, ()))
    feed_aliases = FEED_ALIASES_TO_SLUGS.get(feed_url, {})
    for tag in tags:
        normalized = normalize_category_name(tag.get("term") or "")
        if normalized in ALIASES_TO_SLUGS:
            slugs.add(ALIASES_TO_SLUGS[normalized])
        slugs.update(feed_aliases.get(normalized, ()))
    return slugs
