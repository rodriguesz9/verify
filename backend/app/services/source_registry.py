"""Curated source identity helpers shared by attribution and content risk.

This module never votes on truth. It only recognizes a small explicit set of
publisher families used to label search results and prioritize reference pages.
"""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

SOURCE_FAMILIES = {
    "reuters.com": ("reuters", "editorial"), "apnews.com": ("ap", "editorial"),
    "afp.com": ("afp", "editorial"), "bbc.com": ("bbc", "editorial"),
    "bbc.co.uk": ("bbc", "editorial"), "globo.com": ("globo", "editorial"),
    "uol.com.br": ("uol", "editorial"), "folha.uol.com.br": ("uol", "editorial"),
    "estadao.com.br": ("estadao", "editorial"), "ebc.com.br": ("ebc", "editorial"),
    "cnnbrasil.com.br": ("cnn", "editorial"), "cnn.com": ("cnn", "editorial"),
    "aosfatos.org": ("aosfatos", "editorial"), "boatos.org": ("boatos", "editorial"),
    "agencialupa.org": ("uol", "editorial"), "fullfact.org": ("fullfact", "editorial"),
    "royal.uk": ("royal", "primary"), "bcb.gov.br": ("bcb", "primary"),
    "ibge.gov.br": ("ibge", "primary"), "inpe.br": ("inpe", "primary"),
    "who.int": ("who", "primary"), "nasa.gov": ("nasa", "primary"),
    "planalto.gov.br": ("executivo-br", "primary"),
    "gov.br": ("executivo-br", "primary"),
}
_WIRE = (
    (re.compile(r"\b(?:segundo|conforme|via|fonte|agência|agencia|por|according to|reported by)[\s:/-]+(?:a |the )?Reuters\b|\bReuters\s*[:/]", re.I), "reuters"),
    (re.compile(r"\b(?:segundo|conforme|via|fonte|agência|agencia|por|according to|reported by)[\s:/-]+(?:a |the )?(?:AFP|Agence France.Presse)\b|\bAFP\s*[:/]", re.I), "afp"),
    (re.compile(r"\b(?:segundo|conforme|via|fonte|agência|agencia|por|according to|reported by)[\s:/-]+(?:a |the )?(?:AP|Associated Press)\b|\bAssociated Press\s*[:/]", re.I), "ap"),
)


def source_identity(url):
    """Public-looking curated HTTPS host only; transport safety belongs to fetch."""
    if not isinstance(url, str) or len(url) > 4096 or any(c.isspace() or ord(c) < 32 for c in url):
        return None
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443)
                or not host or "%" in host):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        identity = next((value for domain, value in sorted(SOURCE_FAMILIES.items(), key=lambda x: -len(x[0]))
                         if host == domain or host.endswith("." + domain)), None)
        if not identity:
            return None
        return {"url": urlunsplit(("https", host, parsed.path or "/", parsed.query, "")),
                "publisher_family": identity[0], "source_type": identity[1]}
    except ValueError:
        return None


def source_family(url, body=""):
    """Pure editorial/dependency family label for a curated source."""
    identity = source_identity(url)
    if not identity:
        return None
    if isinstance(body, str):
        for pattern, agency in _WIRE:
            if pattern.search(body[:50000]):
                return agency
    return identity["publisher_family"]
