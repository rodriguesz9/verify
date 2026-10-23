"""Literal statements found in bounded public pages, never votes on truth.

Search titles/snippets identify retrieval leads only. A match requires the full
literal input sentence in fetched visible article text. Source repetition does
not establish accuracy, independence, authorship or agreement with the article.
"""
import asyncio
from datetime import datetime, timezone
import re
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException
import httpx

from app.services.claim_policy import input_claims, normalize_claim
from app.services.public_fetch import fetch_public_resource

ATTRIBUTION_VERSION = "literal_source_attribution_v1"
MAX_SOURCES = 3
MAX_RECOVERY_SOURCES = 10  # AI-directed research can spend four further attempts.
MAX_MATCHES = 3
MAX_INPUT_SEGMENTS = 8
MAX_CLAIM_CHARACTERS = 1000
MAX_SOURCE_CHARACTERS = 50000
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_REFERENCE_ANCHORS = 200
MAX_REFERENCE_LEADS = 12
FETCH_TIMEOUT_SECONDS = 8.0
_ALLOWED_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
_HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))"
    r"\s*(?:!\s*important\s*)?(?:;|$)", re.I,
)
_CONSENT_UI = re.compile(
    r"(?:^|[-_\s])(?:cookie[-_]?(?:banner|consent|notice|dialog|modal)|"
    r"consent[-_]?(?:banner|notice|dialog|modal))(?:$|[-_\s])", re.I,
)
_PUBLICATION_DATE_TEXT = re.compile(
    r"^(?:publicad[oa]|publica[çc][ãa]o|atualizad[oa]|[úu]ltima atualiza[çc][ãa]o|published|updated|last updated|last modified)\b",
    re.I,
)
_PUBLICATION_DATE_PROPERTIES = {"datepublished", "datemodified", "datecreated"}
_PUBLICATION_DATE_UI = re.compile(
    r"(?:^|[-_\s])(?:date[-_]?(?:published|modified|created)|publication[-_]date|"
    r"publish[-_]date|updated[-_]at|data[-_](?:publica[çc][aã]o|atualiza[çc][aã]o))"
    r"(?:$|[-_\s])", re.I,
)
_PUBLISHED_DATE_UI = re.compile(
    r"(?:^|[-_\s])(?:date[-_]?published|publication[-_]date|"
    r"publish[-_]date|data[-_]publica[çc][aã]o)(?:$|[-_\s])", re.I,
)
_AUTHOR_UI = re.compile(
    r"(?:^|[-_\s])(?:byline|author|authors|autoria|autor|autores|credit|credits)"
    r"(?:$|[-_\s])", re.I,
)
_HEADING_UI = re.compile(
    r"(?:^|[-_\s])(?:headline|title|subtitle|subheading|standfirst|dek)(?:$|[-_\s])", re.I,
)
_CAPTION_UI = re.compile(r"(?:^|\s)(?:mc-image-caption|media-caption|wp-caption-text|content-media__description)(?:$|\s)", re.I)
_EDITORIAL_CALLOUT_UI = re.compile(
    r"(?:^|[-_\s])(?:featured[-_](?:story|article)|editorial[-_](?:callout|story)|"
    r"story[-_](?:callout|feature)|article[-_]callout)(?:$|[-_\s])", re.I,
)
_EDITORIAL_READ_ACTION = re.compile(
    r"^(?:read\s+(?:(?:the|full|this)\s+)?(?:story|article|report)|"
    r"(?:leia|ler)\s+(?:(?:a|o)\s+)?(?:matéria|materia|reportagem|artigo|relatório|relatorio))$", re.I,
)
_ADVERTISING_UI = re.compile(
    r"(?:^|[-_\s])(?:ad|ads|advert|advertisement|advertising|sponsored|sponsor|"
    r"anuncio|anúncio|publicidade)(?:$|[-_\s])", re.I,
)
_EDITORIAL_GENERIC_TOPICS = set(
    "mission missão missao flight voo telescope telescópio telescopio space espacial station estação "
    "report relatório relatorio article artigo story matéria materia read leia launch lançamento".split()
)
_AUTHOR_TEXT = re.compile(r"^(?:por|by)\s+[^.!?]{1,200}$", re.I)
_CALENDAR_NAMES = r"janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
_DISCOVERY_MONTHS = {name: index for index, names in enumerate((
    "janeiro january jan", "fevereiro february fev feb", "março marco march mar",
    "abril april abr apr", "maio may", "junho june jun", "julho july jul",
    "agosto august ago aug", "setembro september set sep sept",
    "outubro october out oct", "novembro november nov", "dezembro december dez dec",
), 1) for name in names.split()}
_STANDALONE_DATE = re.compile(
    r"^(?:\d{1,2}\s+(?:de\s+)?(?:" + _CALENDAR_NAMES + r")\.?\s+(?:de\s+)?\d{4}"
    r"|(?:" + _CALENDAR_NAMES + r")\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})"
    r"(?:\s+RELEASE\s*\d{2,4}-\d{1,5})?[.\s]*$", re.I,
)
_BLOCK_TAGS = {"p", "li", "dd", "dt", "blockquote", "figcaption", "caption",
               "h1", "h2", "h3", "h4", "h5", "h6", "table"}
# These containers establish DOM boundaries even without a paragraph below
# them. Flattening a header/div can otherwise swallow a nested explicit
# byline and join its publication date to the first body sentence.
_FLOW_CONTAINERS = {"article", "main", "section", "div", "header", "address"}
_CONTEXT_TAGS = {"blockquote", "figcaption", "caption", "dt", "h1", "h2", "h3", "h4", "h5", "h6"}
_LIVEBLOG_BODY_UI = {"liveblog-body", "js-liveblog-body", "live-blog-body",
                    "liveblog-updates", "live-blog-updates"}
_UNFINISHED_CONTEXT = re.compile(
    r"\b(?:falso|falsa|false|boato|rumou?r|alega|alegou|afirma|claim|claims|"
    r"segundo|according|mensagem|message|n[aã]o|not)\b", re.I,
)
_SEARCH_FAILURES = {
    "not_configured": "Busca de referências não configurada.",
    "timeout": "Busca de referências excedeu o prazo.",
    "rate_limited": "Busca de referências limitada pelo serviço.",
    "invalid_response": "Busca de referências retornou resposta inválida.",
    "error": "Busca de referências indisponível.",
}


def _canonical_url(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        return None
    if any(char.isspace() or ord(char) < 32 for char in value):
        return None
    try:
        url = httpx.URL(value)
        if (url.scheme not in {"http", "https"} or not url.host or url.userinfo
                or url.port not in {None, 80, 443} or "%" in url.host):
            return None
        return str(url.copy_with(fragment=None))
    except (httpx.InvalidURL, ValueError):
        return None


def _literal_candidates(text, queries):
    segments = input_claims(text)
    eligible = {}
    for segment in segments:
        if (20 <= len(segment) <= MAX_CLAIM_CHARACTERS
                and len(re.findall(r"[^\W\d_]+", segment, re.UNICODE)) >= 4):
            eligible.setdefault(normalize_claim(segment), segment)
    ordered = {}
    for query in queries if isinstance(queries, (list, tuple)) else []:
        if not isinstance(query, str) or not query.strip() or query.strip() not in text:
            continue
        for segment in input_claims(query):
            key = normalize_claim(segment)
            if key in eligible:
                ordered.setdefault(key, eligible[key])
    for key, segment in eligible.items():
        ordered.setdefault(key, segment)
    return list(ordered.items())[:MAX_INPUT_SEGMENTS], len(segments), len(eligible)


def _inside(tag, root):
    return tag is root or any(parent is root for parent in tag.parents)


def _visible_text(tag):
    # Whitespace belongs to the visible DOM text, not every inline-node
    # boundary: "1" + <strong>"6"</strong> is 16, never the quantities 1 and 6.
    # The parser replaces <br> with a real whitespace boundary beforehand.
    return re.sub(r"\s+", " ", tag.get_text("", strip=False)).strip()


def _liveblog_region(soup):
    """An explicit update stream with its own visible, dated entry headers.

    Entry clocks delimit updates; they never supply an event date. Refuse a
    mixed/undated stream rather than concatenate unrelated article bodies.
    """
    def visible(tag):
        for node in [tag, *tag.parents]:
            if not isinstance(node, Tag):
                continue
            if (node.name in {"head", "script", "style", "template", "noscript", "nav", "aside",
                              "footer", "form", "video", "audio", "dialog"}
                    or node.has_attr("hidden") or str(node.get("aria-hidden", "")).casefold() == "true"
                    or _HIDDEN_STYLE.search(str(node.get("style", "")))):
                return False
        return True

    regions = []
    for region in [soup, *soup.find_all(["div", "section", "main"])]:
        identifiers = {str(region.get("id", "")), *region.get("class", [])}
        if not identifiers & _LIVEBLOG_BODY_UI or not visible(region):
            continue
        entries = [entry for entry in region.find_all("article")
                   if not entry.find_parent("article") or not _inside(entry.find_parent("article"), region)]
        if len(entries) < 2:
            continue
        headers = []
        for entry in entries:
            header = entry.find("header", recursive=False)
            if header is None or not visible(header):
                break
            for clock in header.find_all("time", datetime=True):
                value = str(clock.get("datetime", ""))
                if not visible(clock) or not _visible_text(clock) or not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T ])", value):
                    continue
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    continue
                headers.append(header)
                break
            else:
                break
        if len(headers) == len(entries):
            regions.append((region, headers))
    return max(regions, key=lambda item: (len(item[0].find_all("p")), len(_visible_text(item[0])))) if regions else (None, [])


def _body_root(soup):
    def paragraph_size(tag):
        return sum(len(_visible_text(paragraph)) for paragraph in tag.find_all("p"))

    # Only visible DOM text is used. An articleBody property in JSON-LD, title,
    # description or other metadata cannot supply article-body evidence.
    explicit = [tag for tag in soup.find_all(True)
                if "articlebody" in {value.casefold() for value in str(tag.get("itemprop", "")).split()}
                and _visible_text(tag)]
    liveblog, _ = _liveblog_region(soup)
    if liveblog is not None:
        root = liveblog
    elif explicit:
        root = max(explicit, key=lambda tag: (paragraph_size(tag), len(_visible_text(tag))))
    else:
        articles = [tag for tag in soup.find_all("article") if _visible_text(tag)]
        root = max(articles, key=lambda tag: (paragraph_size(tag), len(_visible_text(tag)))) if articles else (
            soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup)
    # Keep nearby headings and author/wire credits as context, not selectable
    # statements. Choosing articleBody must not erase a preceding denial.
    scope = root if root.name == "article" else root.find_parent("article")
    scope = scope or root.find_parent("main") or root
    return root, scope


def _append_article_block(blocks, text, role):
    """Separate an explicit numbered provision from its normative preamble.

    Some legislative HTML puts a complete preamble and ``Art. N`` in one
    paragraph. Only a narrow normative introduction ending ``Lei seguinte:``
    can establish this structural boundary; arbitrary prose before ``Art.``
    cannot. Preserve every prefix word as context, including denials, quoted
    or hypothetical identities. Heading/caption/quoted article roles remain
    context. The operative provision is a literal substring, not a rewrite.
    """
    boundary = re.search(
        r"\b(?:decretou|decreta|decretam|sanccionou|sancionou|promulgou|aprovou|aprova)"
        r"\b[^.!?]{0,240}\blei\s+seguinte\s*:\s+"
        r"(?=art\.\s+\d{1,3}(?:[º°]|\.?\s))", text, re.I,
    )
    if boundary:
        # Whitespace is already normalized; no punctuation or article number
        # is invented. The prefix stays in the document and guard context.
        prefix, provision = text[:boundary.end()].rstrip(), text[boundary.end():]
        blocks.append((prefix, "context"))
        blocks.append((provision, role))
    else:
        blocks.append((text, role))


def _article_blocks(root, scope):
    blocks = []
    liveblog, liveblog_headers = _liveblog_region(scope)
    entry_header_ids = {id(header) for header in liveblog_headers}
    entry_ids = {id(header.parent) for header in liveblog_headers}

    def block_role(tag, contextual):
        # A stream can also contain a key-events carousel or other UI before
        # and between updates. Only the validated entry articles supply body;
        # retain the remaining visible text as context, without flattening the
        # whole stream container and swallowing its nested article bodies.
        outside_entry = (liveblog is not None and _inside(tag, liveblog)
                         and not any(id(node) in entry_ids for node in [tag, *tag.parents]))
        return "context" if contextual or not _inside(tag, root) or outside_entry else "body"

    def visit(tag, inherited_context=False):
        identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
        properties = {value.casefold() for value in str(tag.get("itemprop", "")).split()}
        contextual = (inherited_context or id(tag) in entry_header_ids
                      or tag.name in _CONTEXT_TAGS or tag.name == "table"
                      or bool(_AUTHOR_UI.search(identifiers)) or bool(_HEADING_UI.search(identifiers))
                      or bool(_CAPTION_UI.search(identifiers))
                      or tag.name in _BLOCK_TAGS and tag.find(class_=_CAPTION_UI) is not None
                      or "author" in properties)
        if tag.name in _BLOCK_TAGS or contextual:
            text = _visible_text(tag)
            if text:
                role = block_role(tag, contextual or bool(_AUTHOR_TEXT.fullmatch(text)))
                _append_article_block(blocks, text, role)
            return
        # Text-only article containers also occur in static HTML. Preserve DOM
        # order without joining a headline/byline into the first body sentence.
        pending = []

        def flush():
            text = re.sub(r"\s+", " ", "".join(pending)).strip()
            if text:
                _append_article_block(blocks, text, block_role(tag, contextual))
            pending.clear()

        for child in tag.children:
            if isinstance(child, NavigableString):
                # Comments/declarations are not rendered text. Keep ordinary
                # whitespace nodes because they may separate inline words.
                if type(child) is NavigableString:
                    pending.append(str(child))
            elif isinstance(child, Tag):
                # Inline elements remain part of the same text fragment. A
                # child containing a block is traversed rather than duplicated.
                if (child.name not in _BLOCK_TAGS | _FLOW_CONTAINERS
                        and not child.find(list(_BLOCK_TAGS | _FLOW_CONTAINERS))
                        and not _inside(root, child) and not (
                        _AUTHOR_UI.search(" ".join([str(child.get("id", "")), *child.get("class", [])]))
                        or _HEADING_UI.search(" ".join([str(child.get("id", "")), *child.get("class", [])]))
                        or _CAPTION_UI.search(" ".join([str(child.get("id", "")), *child.get("class", [])]))
                        or "author" in str(child.get("itemprop", "")).casefold().split())):
                    text = child.get_text("", strip=False)
                    if text:
                        pending.append(text)
                else:
                    flush()
                    visit(child, contextual)
        flush()

    visit(scope)
    return blocks


def _external_context(scope):
    """Keep nearby page headings/credits without reading other article cards."""
    blocks = []
    branch = scope
    for parent in scope.parents:
        if not isinstance(parent, Tag) or parent.name not in {"main", "section", "div", "body", "[document]"}:
            break
        level = []
        for sibling in reversed(list(branch.previous_siblings)):
            if not isinstance(sibling, Tag) or sibling.name == "article" or sibling.find("article"):
                continue
            identifiers = " ".join([str(sibling.get("id", "")), *sibling.get("class", [])])
            properties = {value.casefold() for value in str(sibling.get("itemprop", "")).split()}
            text = _visible_text(sibling)
            if (sibling.name in {"header", "h1", "h2", "h3", "h4", "h5", "h6"}
                    or sibling.find(["h1", "h2", "h3", "h4", "h5", "h6"])
                    or _AUTHOR_UI.search(identifiers) or _HEADING_UI.search(identifiers) or "author" in properties
                    or _AUTHOR_TEXT.fullmatch(text)
                    or sibling.name == "p" and _UNFINISHED_CONTEXT.search(text)):
                level.extend((value, "context") for value, _ in _article_blocks(sibling, sibling))
        blocks = level + blocks
        branch = parent
        if parent.name in {"main", "body", "[document]"}:
            break
    return blocks


def _block_sentences(blocks):
    sentences, roles = [], []
    pending_body = ""
    unfinished_context = False
    for block, role in blocks:
        # A standalone date is metadata/context, not an unfinished sentence
        # to concatenate into the next paragraph's event. Keep it visible to
        # the comparison without ever borrowing it as a body date.
        if _STANDALONE_DATE.fullmatch(block):
            role = "context"
        if role == "context":
            if pending_body:
                sentences.append(pending_body)
                roles.append("body")
                pending_body = ""
            parts = _source_statements(block)
            sentences.extend(parts)
            roles.extend(["context"] * len(parts))
            if not re.search(r"[.!?][\"”’)]?$", block) and _UNFINISHED_CONTEXT.search(block):
                unfinished_context = True
            continue
        if unfinished_context:
            # An unfinished heading such as "Falso que:" cannot expose its
            # next positive paragraph as standalone endorsing body evidence.
            parts = _source_statements(block)
            sentences.extend(parts)
            roles.extend(["context"] * len(parts))
            unfinished_context = False
            continue
        parts = _source_statements((pending_body + " " + block).strip())
        pending_body = ""
        if parts and not re.search(r"[.!?][\"”’)]?$", parts[-1]):
            pending_body = parts.pop()
        sentences.extend(parts)
        roles.extend(["body"] * len(parts))
    if pending_body:
        sentences.append(pending_body)
        roles.append("body")
    return sentences, roles


def _source_statements(text):
    """Keep a numbered legal article attached to its literal provision.

    ``Art.`` is punctuation within an article identifier, not the end of a
    factual statement. Mask only that exact abbreviation before an explicit
    Arabic article number; restore it before returning any source excerpt.
    Arbitrary abbreviations, cross-paragraph text and source wording are not
    rewritten. In particular, article 2 cannot acquire article 1's identifier.
    """
    marker = "\ue000"
    if marker in text:
        return input_claims(text)
    masked = re.sub(r"\b(art)\.(?=\s+\d{1,3}(?:[º°]|\.?\s))",
                    lambda match: match[1] + marker, text, flags=re.I)
    # A civil clock followed by a zone/date is still one literal statement:
    # splitting at "a.m. EST on ..." detached the launch from its full date.
    # Mask only this closed abbreviation construction, not arbitrary initials
    # or the final period before a new sentence. No DOM blocks are joined.
    masked = re.sub(
        r"\b\d{1,2}:\d{2}\s+[ap]\.m\.(?=\s+(?:UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT|BRT)\s+(?:on|em)\s+)",
        lambda match: match[0].replace(".", marker), masked, flags=re.I,
    )
    return [part.replace(marker, ".") for part in input_claims(masked)]


def _player_caption(tag):
    """Recognize a standalone player caption, never words in article prose.

    The caption paragraph, its dedicated container and an explicit player
    ancestor must agree. Keep inline captions, quoted/contextual blocks and
    ordinary paragraphs, including other children of the same container.
    """
    if tag.name != "p" or "codex-caption" not in tag.get("class", []):
        return False
    container = tag.parent
    if (not isinstance(container, Tag) or container.name != "div"
            or "cxm-block-video__caption-container" not in container.get("class", [])
            or tag.find_parent(list(_BLOCK_TAGS)) is not None):
        return False
    video_types = {"http://schema.org/videoobject", "https://schema.org/videoobject"}
    return any("cxm-block-video" in ancestor.get("class", []) or any(
        value.casefold().rstrip("/") in video_types for value in str(ancestor.get("itemtype", "")).split())
        for ancestor in container.parents if isinstance(ancestor, Tag))


def _bbc_reference_markup(tag, source_url):
    """Recognize one escaped legacy BBC Mundo read-more widget in its own p.

    The visible serialized XML is UI, not quoted article prose or a real DOM
    link. Require the complete closed structure; never erase a prefix, suffix,
    inline qualifier or a quoted example, and never interpret it as HTML.
    """
    hosts = {"bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk"}
    source = _canonical_url(source_url)
    if (tag.name != "p" or tag.find(True) is not None or tag.find_parent(list(_BLOCK_TAGS)) is not None
            or source is None or urlsplit(source).hostname not in hosts
            or not urlsplit(source).path.startswith("/mundo/")):
        return False
    text = _visible_text(tag)
    if not text.startswith('<link type="page">') or len(text) > 4096:
        return False
    try:
        reference = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return False
    if (reference.tag != "link" or reference.attrib != {"type": "page"}
            or (reference.text or "").strip() or len(reference) != 2):
        return False
    caption, target = reference
    if (caption.tag != "caption" or caption.attrib or len(caption)
            or not re.match(r"^Lea también:\s+\S", (caption.text or "").strip())
            or (caption.tail or "").strip() or target.tag != "url" or len(target)
            or (target.text or "").strip() or (target.tail or "").strip()
            or set(target.attrib) != {"href", "platform"} or target.get("platform") != "highweb"):
        return False
    destination = _canonical_url(target.get("href"))
    return (destination is not None and urlsplit(destination).hostname in hosts
            and urlsplit(destination).path.startswith("/mundo/"))


def _article_parts(resource, *, provenance=None):
    try:
        document = resource.data.decode(resource.encoding, errors="replace")
    except LookupError:
        document = resource.data.decode("utf-8", errors="replace")
    title = ""
    if resource.content_type == "text/plain":
        text = re.sub(r"\s+", " ", document).strip()
        truncated = len(text) > MAX_SOURCE_CHARACTERS
        sentences = _source_statements(text[:MAX_SOURCE_CHARACTERS])
        roles = ["body"] * len(sentences)
    else:
        soup = BeautifulSoup(document, "html.parser")
        title = soup.title.get_text(" ", strip=True)[:300] if soup.title else ""
        _, liveblog_headers = _liveblog_region(soup)
        # Retain the actual visible header text as context between updates.
        # Removing every <time> here would erase the only block boundary.
        liveblog_context_nodes = {id(node) for header in liveblog_headers
                                 for node in [header, *header.find_all(True)]}
        for tag in list(soup.find_all(True)):
            if tag.attrs is None:
                continue
            identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
            properties = {value.casefold() for value in str(tag.get("itemprop", "")).split()}
            # Publication/maintenance dates must not become a date of the
            # narrated event by concatenation. Keep inline <time> in narrative
            # paragraphs unless explicitly marked as publication metadata.
            publication_date = bool(properties & _PUBLICATION_DATE_PROPERTIES) or (
                tag.name == "time" and (tag.find_parent("p") is None
                                        or _PUBLICATION_DATE_TEXT.search(tag.get_text(" ", strip=True)))) or (
                bool(_PUBLICATION_DATE_UI.search(identifiers))) or (
                tag.name in {"p", "span", "div"} and not tag.find("p")
                and _PUBLICATION_DATE_TEXT.search(tag.get_text(" ", strip=True)))
            global_navigation = (tag.name == "header" and not tag.find_parent("article")
                and not tag.find("h1") and not _UNFINISHED_CONTEXT.search(_visible_text(tag))
                and (tag.find("nav") is not None or tag.find(attrs={"role": "navigation"}) is not None))
            if (tag.name in {"script", "style", "nav", "footer", "aside", "form", "template", "video", "audio",
                             "noscript", "head", "dialog", "button", "input", "select", "textarea"}
                    or tag.has_attr("hidden")
                    or str(tag.get("aria-hidden", "")).lower() == "true"
                    or str(tag.get("role", "")).lower() == "dialog"
                    or _HIDDEN_STYLE.search(str(tag.get("style", "")))
                    or _CONSENT_UI.search(identifiers)
                    or _player_caption(tag)
                    or _bbc_reference_markup(tag, resource.final_url)
                    or publication_date and id(tag) not in liveblog_context_nodes or global_navigation):
                tag.decompose()
        for line_break in soup.find_all("br"):
            line_break.replace_with(" ")
        root, scope = _body_root(soup)
        if isinstance(provenance, dict):
            from app.services.source_corroboration import _PHOTO_CREDIT_START, _isolated_photo_credit
            fragments = []
            # Only explicit visible media units can mark photo provenance.
            # Keep their full text/roles in the evidence context below; remove
            # only independently validated credit suffixes from agency checks.
            for tag in scope.find_all(True):
                identifiers = " ".join(tag.get("class", []))
                if tag.name != "figcaption" and not _CAPTION_UI.search(identifiers):
                    continue
                text = _visible_text(tag)
                for marker in _PHOTO_CREDIT_START.finditer(text):
                    if re.search(r"\b(?:texto|reportagem|redação|autoria|text|reporting|written|article|story)\b",
                                 text[:marker.start()], re.I):
                        continue  # Mixed textual authorship is not photo-only.
                    fragment = text[marker.start():].strip()
                    textual_credit = re.search(r";\s*(?:texto|reportagem|reporting|text)\b", fragment, re.I)
                    if textual_credit:
                        fragment = fragment[:textual_credit.start()].rstrip()
                    if _isolated_photo_credit(fragment) and fragment not in fragments:
                        fragments.append(fragment)
            if len(fragments) <= 64 and sum(map(len, fragments)) <= 4000:
                provenance.update(version="visible_media_credits_v1", media_credit_fragments=fragments)
        blocks = [*_external_context(scope), *_article_blocks(root, scope)]
        text_size = sum(len(text) for text, _ in blocks) + max(0, len(blocks) - 1)
        truncated = text_size > MAX_SOURCE_CHARACTERS
        bounded_blocks, remaining = [], MAX_SOURCE_CHARACTERS
        for text, role in blocks:
            if remaining <= 0:
                break
            bounded_blocks.append((text[:remaining], role))
            remaining -= len(text) + 1
        sentences, roles = _block_sentences(bounded_blocks)
    if truncated and sentences:
        # The cut can precede a decisive qualifier; its last segment cannot match.
        sentences.pop()
        roles.pop()
    return sentences, title, truncated, roles


def _article_sentences(resource):
    # Preserve the existing helper contract; sentence roles are an optional
    # internal document handoff, never public evidence on their own.
    sentences, title, truncated, _ = _article_parts(resource)
    return sentences, title, truncated


def _editorial_reference_title(anchor, root):
    """A bounded, explicit story callout can label a real retrieval link.

    The nearby heading is only a search/ranking hint. It cannot enter article
    sentences or create evidence, aliases or facts about the linked document.
    """
    if not _EDITORIAL_READ_ACTION.fullmatch(_visible_text(anchor)):
        return None
    for container in anchor.parents:
        if not isinstance(container, Tag) or not _inside(container, root):
            break
        identifiers = " ".join([str(container.get("id", "")), *container.get("class", [])])
        if not _EDITORIAL_CALLOUT_UI.search(identifiers):
            continue
        # One local heading and one action establish an association. A list
        # of stories cannot borrow the page heading or a neighbouring title.
        headings = container.find_all(["h2", "h3", "h4", "h5", "h6"], limit=2)
        links = container.find_all("a", href=True, limit=2)
        if len(headings) != 1 or len(links) != 1 or links[0] is not anchor:
            return None
        heading = headings[0]
        if heading.find_next("a") is not anchor:
            return None
        title = _visible_text(heading)
        return title if 8 <= len(title) <= 300 else None
    return None


def _article_reference_leads(resource):
    """Actual visible citations/callouts, never evidence or generated URLs.

    Restrict discovery to curated primary HTTPS documents. Every selected lead
    still goes through the normal DNS-pinned bounded reader and body guards.
    Neither an anchor's wording nor the cited institution supplies a truth vote.
    """
    if resource.content_type not in {"text/html", "application/xhtml+xml"}:
        return []
    from app.services.source_corroboration import source_identity
    try:
        soup = BeautifulSoup(resource.data.decode(resource.encoding, errors="replace"), "html.parser")
    except LookupError:
        return []
    liveblog, _ = _liveblog_region(soup)
    for tag in list(soup.find_all(True)):
        if tag.attrs is None:
            continue
        identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
        if (tag.name in {"script", "style", "head", "nav", "header", "footer", "aside", "form", "template",
                         "video", "audio", "noscript", "dialog", "button", "input", "select", "textarea",
                         "blockquote", "figcaption", "caption"}
                or tag.has_attr("hidden") or str(tag.get("aria-hidden", "")).casefold() == "true"
                or str(tag.get("role", "")).casefold() in {"navigation", "dialog"}
                or _HIDDEN_STYLE.search(str(tag.get("style", ""))) or _CONSENT_UI.search(identifiers)
                or _AUTHOR_UI.search(identifiers)
                or (_HEADING_UI.search(identifiers) and tag.name not in {"h1", "h2", "h3", "h4", "h5", "h6"})
                or _CAPTION_UI.search(identifiers)
                or _player_caption(tag)
                or _ADVERTISING_UI.search(identifiers)
                or "sponsored" in {str(value).casefold() for value in tag.get("rel", [])}
                or re.search(r"(?:^|[-_\s])(?:related|share|social|menu|breadcrumb|teaser|card)(?:$|[-_\s])", identifiers, re.I)):
            tag.decompose()
    root, _ = _body_root(soup)
    # Header removal is intentional for link discovery, but must not turn a
    # previously validated update stream back into just its longest entry.
    if liveblog is not None and liveblog.attrs is not None:
        root = liveblog
    own_url = _canonical_url(resource.final_url)
    references = {}
    for anchor in root.find_all("a", href=True, limit=MAX_REFERENCE_ANCHORS):
        paragraph = anchor.find_parent("p")
        editorial_title = _editorial_reference_title(anchor, root)
        if _EDITORIAL_READ_ACTION.fullmatch(_visible_text(anchor)) and editorial_title is None:
            continue
        if editorial_title is None and (paragraph is None or not _inside(paragraph, root)):
            continue
        title = editorial_title or _visible_text(anchor)
        href = str(anchor.get("href", ""))
        if not title or len(title) > 300 or not href or href.startswith("#"):
            continue
        url = _canonical_url(urljoin(resource.final_url, href))
        identity = source_identity(url)
        if not identity or identity["source_type"] != "primary":
            continue
        parsed = urlsplit(url)
        if parsed.query or not parsed.path.strip("/") or url == own_url:
            continue
        reference = {"link": url, "title": title}
        if editorial_title:
            reference["reference_kind"] = "editorial_callout"
        references.setdefault(url, reference)
        if len(references) >= MAX_REFERENCE_LEADS:
            break
    return list(references.values())


def primary_reference_leads(text, documents, source_url=None, *, excluded_urls=()):
    """Prioritize at most two cited primary bodies with a literal named topic.

    Institution names and generic link text alone cannot consume the reading
    budget. Exclude already attempted/final URLs BEFORE the two-lead cap.
    The caller owns origin/depth and the cumulative page/deadline budget;
    following a referenced document never authorizes recursive discovery.
    """
    from app.services.source_corroboration import source_identity
    if not isinstance(text, str):
        return []
    generic = {"segundo", "the", "uma", "organização", "mundial", "saúde", "brasil",
               "nasa", "oms", "who", "ibge", "copernicus", "copom", "em", "para", "sobre"}
    names = {token.casefold() for token in re.findall(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÀ-ÿ-]{2,}\b", text)
             if token.casefold() not in generic}
    if not names:
        return []
    submitted = _canonical_url(source_url)
    excluded = {_canonical_url(url) for url in excluded_urls} if isinstance(excluded_urls, (list, tuple, set, frozenset)) else set()
    references = {}
    kind_counts = {}
    for document in documents[:MAX_RECOVERY_SOURCES] if isinstance(documents, (list, tuple)) else []:
        if not isinstance(document, dict) or document.get("source_role") == "submitted_source":
            continue
        source = _canonical_url(document.get("url"))
        if not source_identity(source) or source == submitted:
            continue
        for reference in document.get("reference_leads", [])[:MAX_REFERENCE_LEADS]:
            if not isinstance(reference, dict):
                continue
            url = _canonical_url(reference.get("link"))
            identity = source_identity(url)
            if not identity or identity["source_type"] != "primary" or url == submitted or url in excluded:
                continue
            parsed = urlsplit(url)
            if parsed.query or not parsed.path.strip("/"):
                continue
            title = reference.get("title")
            if not isinstance(title, str):
                continue
            editorial = reference.get("reference_kind") == "editorial_callout"
            # An action such as "Read the Story" is generic. Only its local
            # visible title can establish a named topic for a callout; a URL
            # slug alone cannot repair an unrelated/missing heading.
            topic_names = names - _EDITORIAL_GENERIC_TOPICS - set(_CALENDAR_NAMES.split("|")) if editorial else names
            topic = title if editorial else title + " " + parsed.path
            tokens = set(re.findall(r"[^\W\d_]+", topic.casefold(), re.UNICODE))
            if not topic_names.intersection(tokens):
                continue
            method = "editorial_cited_primary_reference" if editorial else "inline_cited_primary_reference"
            # Preserve the first two ordinary inline candidates, rather than
            # silently changing their existing selection order. At most two
            # callouts can compete for the SAME two returned reading leads.
            if url in references or kind_counts.get(method, 0) >= 2:
                continue
            references[url] = {"link": url, "title": title[:300], "retrieval_method": method}
            kind_counts[method] = kind_counts.get(method, 0) + 1
    # A local title naming the topic is a stronger discovery hint than a
    # generic anchor whose URL alone mentions it. This ranks real links only;
    # neither title can establish the linked article's contents or a vote.
    named_topics = names - _EDITORIAL_GENERIC_TOPICS - set(_CALENDAR_NAMES.split("|"))
    return sorted(references.values(), key=lambda reference: -len(named_topics & set(
        re.findall(r"[^\W\d_]+", reference["title"].casefold(), re.UNICODE))))[:2]


def _lead_month_periods(title, path):
    """Explicit title/path dates are discovery hints, never event evidence."""
    year = r"(?:18|19|20)\d{2}"
    month = "(?:" + "|".join(sorted(_DISCOVERY_MONTHS, key=len, reverse=True)) + ")"
    # Normalize separators, not words: September 18, 2024 / setembro de 2024
    # and their URL-slug variants are the same limited discovery hint.
    periods = set()
    for value in (title, path):
        named = re.sub(r"[-_/.,]+", " ", value).casefold()
        periods.update((match[2], _DISCOVERY_MONTHS[match[1]]) for match in re.finditer(
            r"\b(" + month + r")\s+(?:de\s+)?(?:(?:[0-2]?\d|3[01])\s+)?(" + year + r")\b", named))
    periods.update((match[1], int(match[2])) for match in re.finditer(
        r"(?<!\d)(" + year + r")[/-](0[1-9]|1[0-2])(?:[/-]|\b)", path))
    return periods


def _retrieval_priority(text, title, url):
    """Rank unread leads by reference period/topic, not by alleged truth.

    Publication-prefix dates are removed by the neutral discovery helper. A
    release about 2024 should not lose the reading budget to a release about
    2025 merely because both came from the same institution. Titles and URL
    words remain untrusted hints; every factual/date/value guard runs on body.
    """
    from app.services.source_queries import _discovery_subject, neutral_source_query, discovery_target_years
    from app.services.source_corroboration import source_identity
    from app.services.launch_relations import launch_lead_identity_priority
    from app.services.competition_relations import competition_lead_priority
    subject = neutral_source_query(text, preserve_period=True) or text
    path = unquote(urlsplit(url).path)
    lead = title + " " + path
    year_pattern = r"(?<!\d)(?:18|19|20)\d{2}(?!\d)"
    subject_years = discovery_target_years(text)
    lead_years = set(re.findall(year_pattern, lead))
    subject_months = {_DISCOVERY_MONTHS[word.casefold()] for word in re.findall(
        r"[^\W\d_]+", subject, re.UNICODE) if word.casefold() in _DISCOVERY_MONTHS}
    month_priority = 0
    # Do not guess which date belongs to an event with several years/months.
    # For one explicit period: matching leads first, undated leads still
    # eligible, explicitly different periods last. No URL/query date becomes
    # a publication anchor or a fact, and all candidates retain body guards.
    explicit_subject_periods = _lead_month_periods(_discovery_subject(text), "")
    if len(subject_years) == len(subject_months) == len(explicit_subject_periods) == 1:
        requested = (next(iter(subject_years)), next(iter(subject_months)))
        periods = _lead_month_periods(title, path)
        if requested in explicit_subject_periods:
            month_priority = 0 if requested in periods else (2 if periods else 1)
    year_matches = len(subject_years & lead_years)
    unrelated_period = bool(subject_years and lead_years and not year_matches)
    subperiod = r"\b(?:trimestre|trimestral|quarter|quarterly|semestre|semestral|q[1-4])\b"
    narrower_period = bool(re.search(subperiod, lead, re.I) and not re.search(subperiod, subject, re.I))
    words = lambda value: {word.casefold() for word in re.findall(r"[^\W\d_]{3,}", value, re.UNICODE)}
    shared_topics = len(words(subject) & words(lead))
    primary = (source_identity(url) or {}).get("source_type") == "primary"
    # Identity bands precede the three month bands, preserving the existing
    # tuple contract/month ordering for all non-launch or unparsed claims.
    discovery_priority = (3 * launch_lead_identity_priority(text, lead)
                          + 3 * competition_lead_priority(text, lead) + month_priority)
    # The reader accepts HTML/plain text only. An obvious PDF, audio/video or
    # gallery lead must not consume the sole slot ahead of a readable article
    # from the SAME family. This is a queue hint, not a fetch bypass or a vote;
    # such leads remain eligible when no better candidate exists and failures
    # still count against the unchanged attempt ceiling.
    unsupported_format = bool(re.search(
        r"\.(?:pdf|docx?|xlsx?|pptx?|mp[34]|wav|ogg|webm|jpe?g|png|gif)(?:$|/)", path, re.I,
    ) or re.search(r"/(?:galerias?|galleries|videos?|audios?|v)/", path, re.I))
    # An official host cannot repair an unrelated title/path. Previously the
    # primary-source flag preceded topic overlap and ranked an unrelated
    # institutional overview before an article naming the actual subject.
    return (100 * unsupported_format + discovery_priority + 10 * (shared_topics == 0), -year_matches, unrelated_period,
            narrower_period, -shared_topics, not primary)


def _publication_date(resource):
    """Explicit publication metadata only, never update/retrieval/URL dates.

    Used solely to resolve an explicit relative expression in body text. Video
    cards, JSON-LD articleBody and arbitrary hidden prose cannot supply facts.
    Conflicting/invalid dates abstain rather than selecting a convenient one.
    """
    if resource.content_type not in {"text/html", "application/xhtml+xml"}:
        return None
    try:
        soup = BeautifulSoup(resource.data.decode(resource.encoding, errors="replace"), "html.parser")
    except LookupError:
        return None
    _, liveblog_headers = _liveblog_region(soup)
    entry_metadata_ids = {id(node) for header in liveblog_headers for node in [header, *header.find_all(True)]}
    def eligible_visible_date(tag):
        # An update's timestamp is not publication of the whole live blog.
        if id(tag) in entry_metadata_ids:
            return False
        for node in [tag, *tag.parents]:
            if not isinstance(node, Tag):
                continue
            identifiers = " ".join([str(node.get("id", "")), *node.get("class", [])])
            properties = {value.casefold() for value in str(node.get("itemprop", "")).split()}
            if (node.name in {"script", "style", "template", "noscript", "aside", "footer", "nav", "video", "audio"}
                    or "videoobject" in str(node.get("itemtype", "")).casefold()
                    or node.has_attr("hidden") or str(node.get("aria-hidden", "")).lower() == "true"
                    or _HIDDEN_STYLE.search(str(node.get("style", "")))
                    or properties & {"datemodified", "datecreated"}
                    or (_PUBLICATION_DATE_UI.search(identifiers) and not _PUBLISHED_DATE_UI.search(identifiers))):
                return False
        return True
    values = []
    if soup.head:
        for tag in soup.head.find_all("meta"):
            key = str(tag.get("property") or tag.get("name") or tag.get("itemprop") or "").casefold()
            # Parse.ly explicitly defines this as publication metadata, not
            # modification time. Treat it as another candidate, never as a
            # preferred override of conflicting dates from other providers.
            if key in {"article:published_time", "datepublished", "parsely-pub-date"}:
                values.append(str(tag.get("content", "")))
    # Some pages expose a semantic article time without a global head value.
    if not values:
        for tag in soup.find_all("time", attrs={"itemprop": "datePublished"}):
            if eligible_visible_date(tag):
                values.append(str(tag.get("datetime", "")))
    if not values:
        # A short, explicitly labelled visible date beside the article header
        # also occurs in institutional releases. Never use a date in a body
        # paragraph, a video/card or a bare title/URL as publication evidence.
        months = {name: index for index, group in enumerate(("janeiro january", "fevereiro february", "março march", "abril april", "maio may", "junho june", "julho july", "agosto august", "setembro september", "outubro october", "novembro november", "dezembro december"), 1) for name in group.split()}
        calendar = re.compile(r"^(?:Date:\s*)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:de\s+)?(" + "|".join(months) + r")\s+(?:de\s+)?(\d{4})$", re.I)
        for tag in soup.find_all(["span", "div"]):
            identifiers = " ".join(tag.get("class", []))
            if not (re.search(r"(?:^|\s)(?:date|timestamp|details--date)(?:$|\s)", identifiers)
                    or _PUBLISHED_DATE_UI.search(identifiers)) or tag.find_parent(["p", "figure", "figcaption", "blockquote", "aside"]):
                continue
            if not eligible_visible_date(tag):
                continue
            match = calendar.fullmatch(_visible_text(tag))
            if match:
                try:
                    values.append(datetime(int(match[3]), months[match[2].casefold()], int(match[1])).date().isoformat())
                except ValueError:
                    return None
    dates = set()
    for value in values:
        # Some explicit publication properties use a civil timestamp without
        # an offset, e.g. "2022-09-08 14:32:00". Only the stated calendar date
        # is needed here; do not invent a timezone or move it to another day.
        # This does not permit a URL, update time or arbitrary body date to
        # supply publication metadata, nor publication alone to date an event.
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})?)?", value):
            return None
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
        if date > datetime.now().date():
            return None
        dates.add(date.isoformat())
    return next(iter(dates)) if len(dates) == 1 else None


async def _fetch_article(url):
    try:
        resource = await asyncio.wait_for(fetch_public_resource(
            url, max_bytes=MAX_SOURCE_BYTES, max_redirects=3,
            allowed_types=_ALLOWED_TYPES, total_timeout=FETCH_TIMEOUT_SECONDS,
        ), timeout=FETCH_TIMEOUT_SECONDS)
        if len(resource.data) > MAX_SOURCE_BYTES:
            return {"failure": "oversize"}
        if resource.content_type not in _ALLOWED_TYPES:
            return {"failure": "unsupported_content"}
        final_url = _canonical_url(resource.final_url)
        if not final_url:
            return {"failure": "blocked_or_unavailable"}
        editorial_provenance = {}
        sentences, title, truncated, roles = _article_parts(resource, provenance=editorial_provenance)
        return {"url": final_url, "sentences": sentences, "title": title, "truncated": truncated,
                "sentence_roles": roles,
                "editorial_provenance": editorial_provenance,
                "reference_leads": _article_reference_leads(resource),
                "publication_date": _publication_date(resource),
                "retrieved_at": datetime.now(timezone.utc).isoformat()}
    except HTTPException as exc:
        return {"failure": {413: "oversize", 415: "unsupported_content", 504: "timeout"}.get(
            exc.status_code, "blocked_or_unavailable")}
    except (TimeoutError, httpx.TimeoutException):
        return {"failure": "timeout"}
    except Exception:
        return {"failure": "error"}


async def collect_official_copom_record(text, fetched_cache, *, max_sources=3):
    """Two charged public resources, no JavaScript or unbounded API crawl.

    The index only discovers one exact formal-record date. Each reservation,
    including failure/cancellation, spends the SAME request-local read budget
    as article retrieval. Metadata never becomes a synthetic body sentence.
    """
    from app.services.monetary_decisions import parse_copom_claim
    from app.services.official_source_body import (
        COPOM_INDEX_URL, COPOM_MAX_BYTES, COPOM_ALLOWED_TYPES,
        select_copom_reference, copom_detail_url, decode_copom_body,
    )
    claim = parse_copom_claim(text)
    coverage = {"status": "not_requested", "decision_role": "official_record_retrieval_only",
                "max_resources": 2, "new_fetch_count": 0}
    if (claim is None or claim.reference_date > datetime.now(timezone.utc).date().isoformat()
            or not isinstance(fetched_cache, dict) or type(max_sources) is not int
            or not 2 <= max_sources <= MAX_RECOVERY_SOURCES):
        return coverage
    # No cross-request cache, no retry/refund for an earlier failed index.
    if COPOM_INDEX_URL in fetched_cache:
        return {**coverage, "status": "already_attempted"}
    if len(fetched_cache) + 2 > max_sources:
        return {**coverage, "status": "budget_exhausted"}

    async def read_json(url):
        fetched_cache[url] = {"failure": "error"}
        coverage["new_fetch_count"] += 1
        return await asyncio.wait_for(fetch_public_resource(
            url, max_bytes=COPOM_MAX_BYTES, max_redirects=0,
            allowed_types=set(COPOM_ALLOWED_TYPES), total_timeout=FETCH_TIMEOUT_SECONDS),
            timeout=FETCH_TIMEOUT_SECONDS)

    active_url = COPOM_INDEX_URL
    try:
        index = await read_json(active_url)
        reference = select_copom_reference(index, claim.reference_date)
        fetched_cache[active_url] = {"discovery_only": True, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        if reference is None:
            return {**coverage, "status": "no_matching_record"}
        active_url = copom_detail_url(reference)
        if active_url in fetched_cache:
            return {**coverage, "status": "already_attempted"}
        detail = await read_json(active_url)
        record = decode_copom_body(detail, reference)
        sentences, title, truncated, roles = _article_parts(record.resource)
        fetched_cache[active_url] = {"url": active_url, "sentences": sentences, "title": title,
            "truncated": truncated, "sentence_roles": roles, "reference_leads": [],
            "publication_date": None, "official_record": record.official_record,
            "retrieved_at": datetime.now(timezone.utc).isoformat()}
        return {**coverage, "status": "retrieved"}
    except HTTPException as exc:
        fetched_cache[active_url] = {"failure": {413: "oversize", 415: "unsupported_content", 504: "timeout"}.get(
            exc.status_code, "blocked_or_unavailable")}
    except (TimeoutError, httpx.TimeoutException):
        fetched_cache[active_url] = {"failure": "timeout"}
    except Exception:
        fetched_cache[active_url] = {"failure": "error"}
    return {**coverage, "status": "unavailable"}


async def collect_source_attribution(text, queries, source_url=None, *, search_results=None, include_documents=False,
                                     max_sources=MAX_SOURCES, fetched_cache=None):
    """Return exact page excerpts with explicit bounded retrieval coverage.

    ``search_results`` is a list (optionally carrying ``status``/``reason``).
    No search, model, credentials or reputation service is used here.
    """
    if not isinstance(text, str):
        return {"status": "error", "decision_role": "source_attribution_only", "matches": [],
                "reason": "Texto de entrada indisponível para atribuição.",
                "limitations": ["Atribuição de trechos não comprova veracidade."], "coverage": {}}
    candidates, segment_count, eligible_count = _literal_candidates(text, queries)
    submitted = _canonical_url(source_url)
    valid_search_results = isinstance(search_results, (list, tuple))
    search_status = getattr(search_results, "status", "success" if search_results else "no_results")
    if search_results is None:
        search_status = "not_configured"
    elif (not valid_search_results or not isinstance(search_status, str)
          or search_status not in {"success", "no_results", *_SEARCH_FAILURES}):
        search_status = "invalid_response"

    urls = {}
    cited_urls = set()
    invalid_urls = int(bool(source_url) and submitted is None)
    if submitted:
        urls[submitted] = ""
    for item in search_results if valid_search_results else []:
        if not isinstance(item, dict):
            invalid_urls += 1
            continue
        url = _canonical_url(item.get("link") or item.get("url"))
        if not url:
            invalid_urls += 1
            continue
        title = item.get("title")
        urls.setdefault(url, title[:300] if isinstance(title, str) else "")
        if item.get("retrieval_method") in {"inline_cited_primary_reference", "editorial_cited_primary_reference",
                                           "ai_selected_candidate_reference"}:
            cited_urls.add(url)
    source_limit = max_sources if (isinstance(max_sources, int) and not isinstance(max_sources, bool)
                                   and 1 <= max_sources <= MAX_RECOVERY_SOURCES) else MAX_SOURCES
    cache = fetched_cache if isinstance(fetched_cache, dict) else {}
    selected_urls = list(urls)[:source_limit] if candidates else []
    if include_documents and candidates:
        from app.services.source_corroboration import source_family, source_identity, usable_source_families
        # Prefer distinct eligible publishers over three pages of one group;
        # retain the submitted page for attribution, never independent proof.
        preferred = [submitted] if submitted else []
        # A failed/unrelated page must not reserve its publisher's place in
        # recovery. Another page may contain the required body statement, but
        # it will still be ONE family in the final comparison, never two votes.
        families = usable_source_families(text, list(cache.values()), submitted)
        if submitted:
            families.add(source_family(submitted))
        ranked_urls = sorted(urls, key=lambda url: (url not in cited_urls, *_retrieval_priority(text, urls[url], url)))
        # Diversity must not promote an unrelated/unsupported lead ahead of
        # a readable subject match. Diversify within each quality band first,
        # then retain the other ranked candidates in that same band.
        bands = {}
        for candidate in ranked_urls:
            band = (candidate not in cited_urls, _retrieval_priority(text, urls[candidate], candidate)[0])
            bands.setdefault(band, []).append(candidate)
        for band in sorted(bands):
            fresh = [candidate for candidate in bands[band] if candidate not in cache]
            for candidate in fresh:
                family = source_family(candidate)
                if family and family not in families:
                    preferred.append(candidate)
                    families.add(family)
            preferred.extend(fresh)
        # Recovery keeps every previous attempt (including failures) inside the
        # cumulative ceiling. No failed page is retried or silently refunded.
        attempted = [url for url in cache if url in urls]
        # Remaining slots keep the same ranking after publisher diversity;
        # raw search order must not displace another relevant-period page.
        selected_urls = list(dict.fromkeys([*attempted, *preferred, *ranked_urls]))[:source_limit]
    missing = [url for url in selected_urls if url not in cache]
    # A caller can change the lead list between waves; prior attempts still
    # spend this request's ceiling even when those URLs disappeared.
    missing = missing[:max(0, source_limit - len(cache))]
    selected_urls = [url for url in selected_urls if url in cache or url in missing]
    # Charge the finite attempt budget before dispatch. An interrupted batch
    # cannot refund URLs or erase a sibling's already completed response.
    # Generic error means no usable response, not an invented HTTP timeout.
    for url in missing:
        cache[url] = {"failure": "error"}

    async def fetch_and_record(url):
        cache[url] = await _fetch_article(url)

    fetch_tasks = [asyncio.create_task(fetch_and_record(url)) for url in missing]
    try:
        await asyncio.gather(*fetch_tasks)
    except BaseException:
        # Propagate cancellation/errors only after every sibling is stopped.
        # No task may keep fetching after this collection has been abandoned.
        for task in fetch_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*fetch_tasks, return_exceptions=True)
        raise
    fetched = [cache[url] for url in selected_urls]
    failures = {"oversize": 0, "unsupported_content": 0, "timeout": 0,
                "blocked_or_unavailable": 0, "error": 0}
    matches, seen_matches = [], set()
    documents = []
    fetched_count = truncated_count = discovery_only_count = 0
    for requested_url, result in zip(selected_urls, fetched):
        if result.get("discovery_only") is True:
            discovery_only_count += 1
            continue  # An official index is a locator, never a body/source vote.
        if "failure" in result:
            failures[result["failure"]] += 1
            continue
        fetched_count += 1
        truncated_count += int(result["truncated"])
        if include_documents:
            documents.append({**result,
                "source_role": "submitted_source" if submitted in {requested_url, result["url"]}
                               else "retrieved_reference"})
        source_sentences = {}
        for sentence, role in zip(result["sentences"], result.get("sentence_roles", ["body"] * len(result["sentences"]))):
            if role != "body":
                continue
            if len(sentence) <= MAX_CLAIM_CHARACTERS:
                source_sentences.setdefault(normalize_claim(sentence), sentence)
        for key, claim in candidates:
            excerpt = source_sentences.get(key)
            identity = (result["url"], key)
            if excerpt is None or identity in seen_matches:
                continue
            seen_matches.add(identity)
            matches.append({
                "url": result["url"], "title": result["title"] or urls[requested_url] or "Página consultada",
                "excerpt": excerpt, "claim": claim, "match_method": "literal_sentence",
                "source_role": "submitted_source" if submitted in {requested_url, result["url"]}
                               else "retrieved_reference",
                "retrieved_at": result["retrieved_at"],
            })

    coverage = {
        "version": ATTRIBUTION_VERSION, "search_status": search_status,
        "max_sources": source_limit, "max_source_bytes": MAX_SOURCE_BYTES, "candidate_url_count": len(urls),
        "selected_url_count": len(selected_urls), "omitted_url_count": len(urls) - len(selected_urls),
        "new_fetch_count": len(missing), "reused_fetch_count": len(selected_urls) - len(missing),
        "cumulative_fetch_attempt_count": len(cache),
        "invalid_url_count": invalid_urls, "fetched_count": fetched_count,
        "discovery_only_resource_count": discovery_only_count,
        "failed_fetch_count": sum(failures.values()), "fetch_failure_counts": failures,
        "oversize_fetch_count": failures["oversize"], "source_text_truncated_count": truncated_count,
        "literal_segment_count": segment_count, "eligible_claim_count": eligible_count,
        "selected_claim_count": len(candidates), "omitted_claim_count": eligible_count - len(candidates),
        "matches_count": min(len(matches), MAX_MATCHES), "omitted_match_count": max(0, len(matches) - MAX_MATCHES),
    }
    if include_documents:
        coverage["source_selection"] = "distinct_eligible_families_then_other_references"
    limitations = [
        "Trecho publicado na fonte consultada; isso não comprova verdade, autoria, endosso ou independência editorial.",
        f"Comparação literal de até oito frases e {source_limit} páginas; paráfrases e partes não consultadas podem ficar sem correspondência.",
        "Leitura estática de HTML ou texto, até 50.000 caracteres por página; não executa JavaScript nem resolve toda a visibilidade por CSS.",
        "A página submetida não é uma confirmação independente; esta camada não certifica o artigo inteiro nem altera o veredito.",
    ]
    if truncated_count:
        limitations.append("Uma página excedeu o limite de leitura; o segmento no ponto de corte foi descartado.")
    if sum(failures.values()):
        limitations.append("Parte das páginas selecionadas não pôde ser lida com segurança.")
    if search_status in _SEARCH_FAILURES:
        limitations.append(_SEARCH_FAILURES[search_status])

    status = ("found" if matches else "no_results" if not candidates or fetched_count else
              "error" if selected_urls or invalid_urls else
              "not_configured" if search_status == "not_configured" else
              "error" if search_status in _SEARCH_FAILURES else "no_results")
    reason = None if matches else (
        "Nenhuma frase literal elegível foi selecionada para atribuição." if not candidates else
        "As páginas lidas não continham uma frase completa correspondente." if fetched_count else
        "As páginas selecionadas não puderam ser lidas com segurança." if selected_urls or invalid_urls else
        _SEARCH_FAILURES.get(search_status, "A busca não retornou páginas para atribuição."))
    response = {"status": status, "decision_role": "source_attribution_only", "matches": matches[:MAX_MATCHES],
                "reason": reason, "limitations": limitations, "coverage": coverage}
    if include_documents:
        # Internal handoff only. The pipeline removes this before any report,
        # history or signed export: full page bodies are not public results.
        response["_documents"] = documents
    return response
