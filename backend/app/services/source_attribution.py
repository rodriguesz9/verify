"""Literal statements found in bounded public pages, never votes on truth.

Search titles/snippets identify retrieval leads only. A match requires the full
literal input sentence in fetched visible article text. Source repetition does
not establish accuracy, independence, authorship or agreement with the article.
"""
import asyncio
from datetime import datetime, timezone
import re
from urllib.parse import unquote, urljoin, urlsplit

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
_CAPTION_UI = re.compile(r"(?:^|\s)(?:mc-image-caption|media-caption|wp-caption-text)(?:$|\s)", re.I)
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


def _body_root(soup):
    def paragraph_size(tag):
        return sum(len(_visible_text(paragraph)) for paragraph in tag.find_all("p"))

    # Only visible DOM text is used. An articleBody property in JSON-LD, title,
    # description or other metadata cannot supply article-body evidence.
    explicit = [tag for tag in soup.find_all(True)
                if "articlebody" in {value.casefold() for value in str(tag.get("itemprop", "")).split()}
                and _visible_text(tag)]
    if explicit:
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

    def visit(tag, inherited_context=False):
        identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
        properties = {value.casefold() for value in str(tag.get("itemprop", "")).split()}
        contextual = (inherited_context or tag.name in _CONTEXT_TAGS or tag.name == "table"
                      or bool(_AUTHOR_UI.search(identifiers)) or bool(_HEADING_UI.search(identifiers))
                      or bool(_CAPTION_UI.search(identifiers))
                      or tag.name in _BLOCK_TAGS and tag.find(class_=_CAPTION_UI) is not None
                      or "author" in properties)
        if tag.name in _BLOCK_TAGS or contextual:
            text = _visible_text(tag)
            if text:
                role = "context" if contextual or not _inside(tag, root) or _AUTHOR_TEXT.fullmatch(text) else "body"
                _append_article_block(blocks, text, role)
            return
        # Text-only article containers also occur in static HTML. Preserve DOM
        # order without joining a headline/byline into the first body sentence.
        pending = []

        def flush():
            text = re.sub(r"\s+", " ", "".join(pending)).strip()
            if text:
                _append_article_block(blocks, text, "context" if contextual or not _inside(tag, root) else "body")
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
    return [part.replace(marker, ".") for part in input_claims(masked)]


def _article_parts(resource):
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
                    or publication_date or global_navigation):
                tag.decompose()
        for line_break in soup.find_all("br"):
            line_break.replace_with(" ")
        root, scope = _body_root(soup)
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
                or _ADVERTISING_UI.search(identifiers)
                or "sponsored" in {str(value).casefold() for value in tag.get("rel", [])}
                or re.search(r"(?:^|[-_\s])(?:related|share|social|menu|breadcrumb|teaser|card)(?:$|[-_\s])", identifiers, re.I)):
            tag.decompose()
    root, _ = _body_root(soup)
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


def primary_reference_leads(text, documents, source_url=None):
    """Prioritize at most two cited primary bodies with a literal named topic.

    Institution names and generic link text alone cannot consume the reading
    budget. No crawl/recursive traversal: only first-wave documents supply
    these leads, and the caller retains the cumulative six-page ceiling.
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
            if not identity or identity["source_type"] != "primary" or url == submitted:
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


def _retrieval_priority(text, title, url):
    """Rank unread leads by reference period/topic, not by alleged truth.

    Publication-prefix dates are removed by the neutral discovery helper. A
    release about 2024 should not lose the reading budget to a release about
    2025 merely because both came from the same institution. Titles and URL
    words remain untrusted hints; every factual/date/value guard runs on body.
    """
    from app.services.source_queries import neutral_source_query
    from app.services.source_corroboration import source_identity
    subject = neutral_source_query(text, preserve_period=True) or text
    lead = title + " " + unquote(urlsplit(url).path)
    year_pattern = r"(?<!\d)(?:18|19|20)\d{2}(?!\d)"
    subject_years = set(re.findall(year_pattern, subject))
    lead_years = set(re.findall(year_pattern, lead))
    year_matches = len(subject_years & lead_years)
    unrelated_period = bool(subject_years and lead_years and not year_matches)
    subperiod = r"\b(?:trimestre|trimestral|quarter|quarterly|semestre|semestral|q[1-4])\b"
    narrower_period = bool(re.search(subperiod, lead, re.I) and not re.search(subperiod, subject, re.I))
    words = lambda value: {word.casefold() for word in re.findall(r"[^\W\d_]{3,}", value, re.UNICODE)}
    shared_topics = len(words(subject) & words(lead))
    primary = (source_identity(url) or {}).get("source_type") == "primary"
    return (-year_matches, unrelated_period, narrower_period, not primary, -shared_topics)


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
    def eligible_visible_date(tag):
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
            if key in {"article:published_time", "datepublished"}:
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
        sentences, title, truncated, roles = _article_parts(resource)
        return {"url": final_url, "sentences": sentences, "title": title, "truncated": truncated,
                "sentence_roles": roles,
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
        for candidate in ranked_urls:
            if candidate in cache:
                continue
            family = source_family(candidate)
            if family and family not in families:
                preferred.append(candidate)
                families.add(family)
        # Recovery keeps every previous attempt (including failures) inside the
        # cumulative ceiling. No failed page is retried or silently refunded.
        attempted = [url for url in cache if url in urls]
        selected_urls = list(dict.fromkeys([*attempted, *preferred, *urls]))[:source_limit]
    missing = [url for url in selected_urls if url not in cache]
    # A caller can change the lead list between waves; prior attempts still
    # spend this request's ceiling even when those URLs disappeared.
    missing = missing[:max(0, source_limit - len(cache))]
    selected_urls = [url for url in selected_urls if url in cache or url in missing]
    new_results = await asyncio.gather(*[_fetch_article(url) for url in missing])
    cache.update(zip(missing, new_results))
    fetched = [cache[url] for url in selected_urls]
    failures = {"oversize": 0, "unsupported_content": 0, "timeout": 0,
                "blocked_or_unavailable": 0, "error": 0}
    matches, seen_matches = [], set()
    documents = []
    fetched_count = truncated_count = 0
    for requested_url, result in zip(selected_urls, fetched):
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
