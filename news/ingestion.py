"""Lectura y guardado de metadatos de feeds RSS seleccionados."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import feedparser
from django.db import transaction
from django.utils.html import strip_tags

from .category_aliases import category_slugs_for_entry
from .models import Article, Category
from .retention import retention_cutoff


MAX_FEED_BYTES = 2_000_000
MAX_SUMMARY_LENGTH = 600
USER_AGENT = "SitioNoticias/0.1 (proyecto universitario; lector RSS)"
TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class IngestionError(Exception):
    """El feed no se pudo descargar o interpretar."""


@dataclass
class IngestionResult:
    created: int = 0
    duplicates: int = 0
    skipped: int = 0
    unchanged: bool = False


def canonicalize_url(url):
    """Quita fragmentos y parámetros de seguimiento, sin cambiar el enlace original."""
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return ""
    except ValueError:
        return ""

    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_PARAMETERS
        ]
    )
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", query, "")
    )


def publication_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def permitted_summary(entry, feed):
    if not feed.show_summary:
        return ""
    summary = " ".join(unescape(strip_tags(entry.get("summary") or "")).split())
    # Algunos feeds incluyen el artículo completo en este campo.
    return summary if len(summary) <= MAX_SUMMARY_LENGTH else ""


def existing_article(feed, guid, original_url, canonical_url, fingerprint):
    if guid:
        found = Article.objects.filter(feed=feed, guid=guid).first()
        if found:
            return found

    found = Article.objects.filter(original_url=original_url).first()
    if found:
        return found

    found = Article.objects.filter(canonical_url=canonical_url).first()
    if found:
        return found

    # Respaldo para registros antiguos sin URL canónica. Se confirma la URL
    # antes de tratar la huella como duplicado.
    for article in Article.objects.filter(fingerprint=fingerprint):
        if canonicalize_url(article.original_url) == canonical_url:
            return article
    return None


def download_feed(feed, force_download=False):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"}
    if feed.etag and not force_download:
        headers["If-None-Match"] = feed.etag
    if feed.last_modified and not force_download:
        headers["If-Modified-Since"] = feed.last_modified

    try:
        with urlopen(Request(feed.url, headers=headers), timeout=15) as response:
            data = response.read(MAX_FEED_BYTES + 1)
            etag = response.headers.get("ETag", "")[:255]
            last_modified = response.headers.get("Last-Modified", "")[:255]
    except HTTPError as error:
        if error.code == 304:
            error.close()
            return None
        raise IngestionError(f"HTTP {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise IngestionError(f"Error de conexión: {error}") from error

    if len(data) > MAX_FEED_BYTES:
        raise IngestionError("El feed supera el límite de 2 MB")

    parsed = feedparser.parse(data)
    if parsed.bozo or not parsed.version:
        raise IngestionError("El feed no es un RSS/Atom válido")
    return parsed.entries, etag, last_modified


def ingest_feed(feed, force_download=False):
    result = IngestionResult()
    downloaded = download_feed(feed, force_download=force_download)
    if downloaded is None:
        result.unchanged = True
        return result

    entries, etag, last_modified = downloaded
    fallback_slugs = set(feed.categories.values_list("slug", flat=True))
    category_ids_by_slug = dict(Category.objects.values_list("slug", "id"))
    cutoff = retention_cutoff()

    for entry in entries:
        title = (entry.get("title") or "").strip()
        original_url = (entry.get("link") or "").strip()
        canonical_url = canonicalize_url(original_url)
        published_at = publication_date(entry)

        if (
            not title
            or len(title) > 500
            or not canonical_url
            or len(original_url) > 2048
            or len(canonical_url) > 2048
            or published_at is None
            or published_at < cutoff
        ):
            result.skipped += 1
            continue

        guid = (entry.get("id") or "").strip()
        if len(guid) > 512:
            guid = ""
        fingerprint = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        category_slugs = category_slugs_for_entry(entry, fallback_slugs)
        category_ids = [category_ids_by_slug[slug] for slug in category_slugs if slug in category_ids_by_slug]
        article = existing_article(feed, guid, original_url, canonical_url, fingerprint)
        if article:
            if article.feed_id == feed.id:
                article.categories.set(category_ids)
            result.duplicates += 1
            continue

        with transaction.atomic():
            article = Article.objects.create(
                feed=feed,
                guid=guid,
                original_url=original_url,
                canonical_url=canonical_url,
                fingerprint=fingerprint,
                title=title,
                summary=permitted_summary(entry, feed),
                language=(entry.get("language") or "")[:10] or feed.language,
                published_at=published_at,
            )
            article.categories.add(*category_ids)
        result.created += 1

    feed.etag = etag
    feed.last_modified = last_modified
    feed.save(update_fields=["etag", "last_modified"])
    return result
