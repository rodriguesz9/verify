"""Discovery hints about the current reader, not MIME validation or evidence."""
from urllib.parse import unquote, urlsplit


STATIC_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
_NONSTATIC_SUFFIXES = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                      ".zip", ".gz", ".mp3", ".wav", ".mp4", ".webm",
                      ".jpg", ".jpeg", ".png", ".gif", ".webp")


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


def reader_capabilities():
    return {"content_types": sorted(STATIC_CONTENT_TYPES),
            "executes_javascript": False, "extracts_pdf_text": False,
            "url_suffix_is_only_a_discovery_hint": True}
