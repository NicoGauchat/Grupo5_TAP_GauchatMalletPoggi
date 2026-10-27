"""Lectura y guardado de metadatos de feeds RSS seleccionados."""

import hashlib
import re
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
from .models import Article, ArticleOrigin, Category
from .retention import retention_cutoff


MAX_FEED_BYTES = 2_000_000
MAX_SUMMARY_LENGTH = 600
ELDIARIO_DESCRIPTION_FEED = "https://www.eldiario.es/rss/internacional/"
ELDIARIO_LICENSE = "https://creativecommons.org/licenses/by-nc/4.0/"
USER_AGENT = "LibreNews/0.1 (proyecto universitario; lector RSS)"
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
    raw = entry.get("summary") or ""
    summary = " ".join(unescape(strip_tags(raw)).split())
    if getattr(feed, "url", "") == ELDIARIO_DESCRIPTION_FEED:
        # Excepción revisada: usar sólo la primera entradilla propia bajo CC BY-NC.
        # El resto del artículo que viene en el RSS nunca se guarda.
        source = feed.source
        if source.name != "elDiario.es" or source.license_url != ELDIARIO_LICENSE:
            return ""
        author = entry.get("author") or ""
        rights = " ".join(str(entry.get(key) or "") for key in ("rights", "copyright", "source"))
        if not author.strip() or re.search(
            r"\b(?:the\s+guardian|reuters|efe|afp|associated\s+press|europa\s+press|agencias?)\b|theguardian\.com",
            f"{author} {rights} {summary}", re.IGNORECASE,
        ):
            return ""
        if "<" in raw:
            summary = ""
            for paragraph in re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p\s*>", raw, re.IGNORECASE | re.DOTALL):
                text = " ".join(unescape(strip_tags(paragraph.group(1))).split())
                if text:
                    summary = text
                    break
    # Algunos feeds incluyen el artículo completo en este campo.
    return summary if len(summary) <= MAX_SUMMARY_LENGTH else ""


def permitted_image(entry, feed):
    if not feed.show_images:
        return "", ""
    candidates = [(image, field == "media_thumbnail") for field in ("media_content", "media_thumbnail", "enclosures")
                  for image in entry.get(field, [])]
    for image, thumbnail in candidates:
        url = image.get("url") or image.get("href") or ""
        kind = (image.get("type") or "").lower()
        if kind and not kind.startswith("image/"):
            continue
        if image.get("medium", "image") != "image" or not canonicalize_url(url) or len(url) > 2048:
            continue
        if (not kind and not thumbnail and image.get("medium") != "image"
                and not urlsplit(url).path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))):
            continue
        credits = [credit.get("content", "") for credit in entry.get("media_credit", [])]
        credit = " / ".join(text for text in credits if text) or feed.source.name
        return url, " ".join(unescape(strip_tags(credit)).split())[:500]
    return "", ""


def existing_article(feed, guid, original_url, canonical_url, fingerprint):
    if guid:
        origin = ArticleOrigin.objects.filter(feed=feed, guid=guid).select_related("article").first()
        if origin:
            return origin.article
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


def record_origin(article, feed, guid, category_ids):
    """Reclasifica un origen y mantiene los aportes de los demás feeds."""
    # También preserva noticias creadas desde admin después de la migración.
    primary_origin, created = ArticleOrigin.objects.get_or_create(
        article=article, feed_id=article.feed_id, defaults={"guid": article.guid},
    )
    if created:
        primary_origin.categories.set(article.categories.all())

    origin, _ = ArticleOrigin.objects.get_or_create(
        article=article, feed=feed, defaults={"guid": guid},
    )
    # Una respuesta sin GUID no borra el último identificador conocido.
    if guid and origin.guid != guid:
        origin.guid = guid
        origin.save(update_fields=["guid"])
    origin.categories.set(category_ids)
    article.categories.set(
        Category.objects.filter(article_origins__article=article).distinct()
    )


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
        byline = " ".join(unescape(strip_tags(entry.get("author") or "")).split())[:300]
        if len(guid) > 512:
            guid = ""
        fingerprint = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        category_slugs = category_slugs_for_entry(entry, fallback_slugs, feed.url)
        category_ids = [category_ids_by_slug[slug] for slug in category_slugs if slug in category_ids_by_slug]
        article = existing_article(feed, guid, original_url, canonical_url, fingerprint)
        if article:
            with transaction.atomic():
                article = Article.objects.select_for_update().get(pk=article.pk)
                if article.feed_id == feed.pk:
                    article.image_url, article.image_credit = permitted_image(entry, feed)
                    article.byline = byline or article.byline
                    article.summary = permitted_summary(entry, feed)
                    article.save(update_fields=["image_url", "image_credit", "byline", "summary"])
                record_origin(article, feed, guid, category_ids)
            result.duplicates += 1
            continue

        with transaction.atomic():
            image_url, image_credit = permitted_image(entry, feed)
            article = Article.objects.create(
                feed=feed,
                guid=guid,
                original_url=original_url,
                canonical_url=canonical_url,
                fingerprint=fingerprint,
                title=title,
                byline=byline,
                summary=permitted_summary(entry, feed),
                image_url=image_url, image_credit=image_credit,
                language=(entry.get("language") or "")[:10] or feed.language,
                published_at=published_at,
            )
            record_origin(article, feed, guid, category_ids)
        result.created += 1

    feed.etag = etag
    feed.last_modified = last_modified
    feed.save(update_fields=["etag", "last_modified"])
    return result
