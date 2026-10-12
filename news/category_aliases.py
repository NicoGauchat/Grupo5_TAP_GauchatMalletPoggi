"""Etiquetas RSS aceptadas para cada categoría de la aplicación.

Agregar aquí sólo términos observados en feeds revisados. La comparación es
exacta después de normalizar mayúsculas, tildes y espacios.
"""

import unicodedata


CATEGORY_ALIASES = {
    "tecnologia": {"Tecnología", "Computer science and technology"},
    "inteligencia-artificial": {"Inteligencia artificial", "Artificial intelligence"},
    "ciencia": {"Ciencia"},
    "economia": set(),
    "geopolitica": set(),
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


def category_slugs_for_entry(entry, fallback_slugs):
    """Usa etiquetas del elemento; recurre al feed sólo si no hay etiquetas."""
    tags = entry.get("tags") or []
    if not tags:
        return set(fallback_slugs)

    slugs = set()
    for tag in tags:
        normalized = normalize_category_name(tag.get("term") or "")
        if normalized in ALIASES_TO_SLUGS:
            slugs.add(ALIASES_TO_SLUGS[normalized])
    return slugs
