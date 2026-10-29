"""Discovery hints about the current reader, not MIME validation or evidence."""
import re
from urllib.parse import unquote, urlsplit


STATIC_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
_NONSTATIC_SUFFIXES = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                      ".zip", ".gz", ".mp3", ".wav", ".mp4", ".webm",
                      ".jpg", ".jpeg", ".png", ".gif", ".webp")
_PAGINATED_LISTING_PATH = re.compile(
    r"/(?:tudo-sobre|tags?|topics?|category|categories|categorias?|assuntos?|archives?|arquivos?)/"
    r"(?:[^/]+/){0,8}(?:pagina|página|page)/[1-9]\d{0,5}/?$", re.I,
)


def known_unsupported_lead(url):
    """Deprioritize a known file suffix; an extension never proves its MIME.

    Unknown/extensionless links remain candidates. A PDF-looking URL can still
    redirect to HTML and is not removed from ordinary retrieval. The existing
    public fetcher remains responsible for DNS, redirects, bytes and MIME.
    """
    if not isinstance(url, str) or len(url) > 4096:
        return False
    try:
        path = unquote(urlsplit(url).path).casefold()
    except ValueError:
        return False
    return path.endswith(_NONSTATIC_SUFFIXES)


def known_paginated_listing_lead(url):
    """A closed taxonomy/archive pagination path is only a queue tie-break.

    These pages remain readable candidates and may supply actual body text.
    A generic article ending in /page/2 is not enough to identify a listing;
    a literal taxonomy/archive segment and a final numeric page are required.
    Unknown topic/search layouts and query-based pagination stay unclassified.
    """
    if not isinstance(url, str) or len(url) > 4096:
        return False
    try:
        path = unquote(urlsplit(url).path)
    except ValueError:
        return False
    return bool(_PAGINATED_LISTING_PATH.search(path))


def reader_capabilities():
    return {"content_types": sorted(STATIC_CONTENT_TYPES),
            "executes_javascript": False, "extracts_pdf_text": False,
            "url_suffix_is_only_a_discovery_hint": True}
