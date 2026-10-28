"""Closed institutional index-to-original discovery; never article evidence.

Only real visible anchors can supply a destination. The law identity in a
heading labels that reading lead; it does not become the law's article text.
This module has no credential, model, network or decision dependencies.
"""
from datetime import date
import re
from urllib.parse import urljoin, urlsplit, urlunsplit


REFERENCE_KIND = "legislative_original_publication"
RETRIEVAL_METHOD = "legislative_original_reference"
_HOSTS = {"camara.leg.br", "www.camara.leg.br", "www2.camara.leg.br"}
_MONTHS = {name: index for index, name in enumerate((
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
    "agosto", "setembro", "outubro", "novembro", "dezembro"), 1)}
_PATH_MONTHS = {name.replace("ç", "c"): value for name, value in _MONTHS.items()}
_LAW = re.compile(
    r"\blei\s+(?:n[º°.]?\s*)?(\d{1,6}(?:\.\d{3})*),?\s+de\s+"
    r"(\d{1,2})\s+de\s+(" + "|".join(_MONTHS) + r")\s+de\s+(\d{4})\b", re.I)
_ROUTE = re.compile(
    r"^/legin/fed/(?P<kind>lei|leimp)/(?P<first>\d{4})-(?P<last>\d{4})/"
    r"lei-(?P<number>[1-9]\d{0,8})-(?P<day>\d{1,2})-(?P<month>[a-z]+)-"
    r"(?P<year>\d{4})-(?P<record>[1-9]\d*)-"
    r"(?P<suffix>norma-pl\.html|publicacaooriginal-[1-9]\d*-pl\.html)$")
_INDEX_HEADING = re.compile(r"Legislação Informatizada\s*[-–—]\s*Dados da Norma", re.I)
_ORIGIN_LABEL = re.compile(r"Texto\s*[-–—]\s*Publicação Original", re.I)


def _text(tag):
    return " ".join(tag.get_text(" ", strip=True).split())


def _identity(match):
    try:
        return (int(match[1].replace(".", "")),
                date(int(match[4]), _MONTHS[match[3].casefold()], int(match[2])).isoformat())
    except (ValueError, KeyError):
        return None


def claim_law_identity(text):
    """Exactly one complete literal reference, not a name or number alone."""
    if not isinstance(text, str):
        return None
    matches = list(_LAW.finditer(text))
    return _identity(matches[0]) if len(matches) == 1 else None


def _route(url, *, original):
    if (not isinstance(url, str) or not 1 <= len(url) <= 4096
            or any(char.isspace() or ord(char) < 32 for char in url)):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in _HOSTS
                or parsed.port not in {None, 443} or parsed.username or parsed.password
                or parsed.query or parsed.fragment or "?" in url or "#" in url or "%" in parsed.path):
            return None
        match = _ROUTE.fullmatch(parsed.path)
        if match is None or match["suffix"].startswith("publicacaooriginal-") != original:
            return None
        year = int(match["year"])
        if not int(match["first"]) <= year <= int(match["last"]):
            return None
        identity = (int(match["number"]), date(year, _PATH_MONTHS[match["month"]], int(match["day"])).isoformat())
        # The raw paired path also preserves type, period and record identity.
        prefix = parsed.path.rsplit("-" + match["suffix"], 1)[0]
        return {"url": urlunsplit(("https", parsed.hostname, parsed.path, "", "")),
                "host": parsed.hostname, "prefix": prefix, "identity": identity}
    except (ValueError, KeyError):
        return None


def _matching_pair(source_url, target_url, title):
    source, target = _route(source_url, original=False), _route(target_url, original=True)
    heading = _LAW.fullmatch(title) if isinstance(title, str) and len(title) <= 300 else None
    return bool(source and target and heading and source["host"] == target["host"]
                and source["prefix"] == target["prefix"]
                and source["identity"] == target["identity"] == _identity(heading))


def legislative_original_reference(root, source_url, *, max_anchors):
    """Return one DOM anchor and its lead from an already sanitized index.

    Generic portal/popular headings are allowed; only one complete legal
    heading may identify this bounded ficha. Metadata and generated URLs do
    not qualify. The caller retains the existing document/anchor/read limits.
    """
    if (_route(source_url, original=False) is None or not hasattr(root, "find_all")
            or type(max_anchors) is not int or max_anchors < 1):
        return None
    headers = root.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    markers = [tag for tag in headers if _INDEX_HEADING.fullmatch(_text(tag))]
    if len(markers) != 1:
        return None
    container = markers[0].find_next_sibling()
    containers = root.find_all(class_=lambda value: value == "dadosNorma")
    if len(containers) != 1 or container is not containers[0]:
        return None
    headings = [tag for tag in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
                if _LAW.fullmatch(_text(tag))]
    anchors = container.find_all("a", limit=max_anchors + 1)
    origins = [tag for tag in anchors if _ORIGIN_LABEL.fullmatch(_text(tag))]
    if len(headings) != 1 or len(anchors) > max_anchors or len(origins) != 1:
        return None
    anchor, title = origins[0], _text(headings[0])
    href = anchor.get("href")
    if (not isinstance(href, str) or not href or "?" in href or "#" in href
            or anchor.find_parent("a") is not None
            or any(char.isspace() or ord(char) < 32 for char in href)):
        return None
    try:
        target_url = urljoin(source_url, href)
    except ValueError:
        return None
    if not _matching_pair(source_url, target_url, title):
        return None
    return anchor, {"link": _route(target_url, original=True)["url"], "title": title,
                    "reference_kind": REFERENCE_KIND}


def legislative_reference_matches(text, source_url, reference):
    """Recheck a server-extracted lead against the exact requested diploma."""
    if (not isinstance(reference, dict) or reference.get("reference_kind") != REFERENCE_KIND
            or not _matching_pair(source_url, reference.get("link"), reference.get("title"))):
        return False
    requested = claim_law_identity(text)
    return requested is not None and requested == _route(reference["link"], original=True)["identity"]
