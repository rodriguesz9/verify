"""Bounded public-page retrieval for literal attribution and semantic review.

Search titles/snippets identify retrieval leads only. Retrieved article text is
available to semantic review even without a literal match; literal matches
remain useful for exact attribution. Source repetition does not establish
accuracy, independence, authorship or agreement with the article.
"""
import asyncio
from datetime import datetime, timezone
import re

from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException
import httpx

from app.services.claim_policy import input_claims, normalize_claim
from app.services.public_fetch import fetch_public_resource

ATTRIBUTION_VERSION = "literal_source_attribution_v1"
MAX_SOURCES = 3
MAX_SOURCE_LIMIT = 6
MAX_MATCHES = 3
MAX_INPUT_SEGMENTS = 8
MAX_CLAIM_CHARACTERS = 1000
MAX_SOURCE_CHARACTERS = 50000
MAX_SOURCE_BYTES = 2 * 1024 * 1024
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
_AUTHOR_UI = re.compile(
    r"(?:^|[-_\s])(?:byline|author|authors|autoria|autor|autores|credit|credits)"
    r"(?:$|[-_\s])", re.I,
)
_HEADING_UI = re.compile(
    r"(?:^|[-_\s])(?:headline|title|subtitle|subheading|standfirst|dek)(?:$|[-_\s])", re.I,
)
_AUTHOR_TEXT = re.compile(r"^(?:por|by)\s+[^.!?]{1,200}$", re.I)
_BLOCK_TAGS = {"p", "li", "dd", "dt", "blockquote", "figcaption", "caption",
               "h1", "h2", "h3", "h4", "h5", "h6", "table"}
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
            soup.find("main") or soup.body or soup)
    # Keep nearby headings and author/wire credits as context, not selectable
    # statements. Choosing articleBody must not erase a preceding denial.
    scope = root if root.name == "article" else root.find_parent("article")
    scope = scope or root.find_parent("main") or root
    return root, scope


def _article_blocks(root, scope):
    blocks = []

    def visit(tag, inherited_context=False):
        identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
        properties = {value.casefold() for value in str(tag.get("itemprop", "")).split()}
        contextual = (inherited_context or tag.name in _CONTEXT_TAGS or tag.name == "table"
                      or bool(_AUTHOR_UI.search(identifiers)) or bool(_HEADING_UI.search(identifiers))
                      or "author" in properties)
        if tag.name in _BLOCK_TAGS or contextual:
            text = _visible_text(tag)
            if text:
                role = "context" if contextual or not _inside(tag, root) or _AUTHOR_TEXT.fullmatch(text) else "body"
                blocks.append((text, role))
            return
        # Text-only article containers also occur in static HTML. Preserve DOM
        # order without joining a headline/byline into the first body sentence.
        pending = []

        def flush():
            text = re.sub(r"\s+", " ", "".join(pending)).strip()
            if text:
                blocks.append((text, "context" if contextual or not _inside(tag, root) else "body"))
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
                if (child.name not in _BLOCK_TAGS and not child.find(list(_BLOCK_TAGS))
                        and not _inside(root, child) and not (
                        _AUTHOR_UI.search(" ".join([str(child.get("id", "")), *child.get("class", [])]))
                        or _HEADING_UI.search(" ".join([str(child.get("id", "")), *child.get("class", [])]))
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
        if not isinstance(parent, Tag) or parent.name not in {"main", "section", "div", "body"}:
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
        if parent.name in {"main", "body"}:
            break
    return blocks


def _block_sentences(blocks):
    sentences, roles = [], []
    pending_body = ""
    unfinished_context = False
    for block, role in blocks:
        if role == "context":
            if pending_body:
                sentences.append(pending_body)
                roles.append("body")
                pending_body = ""
            parts = input_claims(block)
            sentences.extend(parts)
            roles.extend(["context"] * len(parts))
            if not re.search(r"[.!?][\"”’)]?$", block) and _UNFINISHED_CONTEXT.search(block):
                unfinished_context = True
            continue
        if unfinished_context:
            # An unfinished heading such as "Falso que:" cannot expose its
            # next positive paragraph as standalone endorsing body evidence.
            parts = input_claims(block)
            sentences.extend(parts)
            roles.extend(["context"] * len(parts))
            unfinished_context = False
            continue
        parts = input_claims((pending_body + " " + block).strip())
        pending_body = ""
        if parts and not re.search(r"[.!?][\"”’)]?$", parts[-1]):
            pending_body = parts.pop()
        sentences.extend(parts)
        roles.extend(["body"] * len(parts))
    if pending_body:
        sentences.append(pending_body)
        roles.append("body")
    return sentences, roles


def _article_parts(resource):
    try:
        document = resource.data.decode(resource.encoding, errors="replace")
    except LookupError:
        document = resource.data.decode("utf-8", errors="replace")
    title = ""
    if resource.content_type == "text/plain":
        text = re.sub(r"\s+", " ", document).strip()
        truncated = len(text) > MAX_SOURCE_CHARACTERS
        sentences = input_claims(text[:MAX_SOURCE_CHARACTERS])
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
            if (tag.name in {"script", "style", "nav", "footer", "aside", "form", "template", "video", "audio",
                             "noscript", "head", "dialog", "button", "input", "select", "textarea"}
                    or tag.has_attr("hidden")
                    or str(tag.get("aria-hidden", "")).lower() == "true"
                    or str(tag.get("role", "")).lower() == "dialog"
                    or _HIDDEN_STYLE.search(str(tag.get("style", "")))
                    or _CONSENT_UI.search(identifiers)
                    or publication_date):
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
                "retrieved_at": datetime.now(timezone.utc).isoformat()}
    except HTTPException as exc:
        return {"failure": {413: "oversize", 415: "unsupported_content", 504: "timeout"}.get(
            exc.status_code, "blocked_or_unavailable")}
    except (TimeoutError, httpx.TimeoutException):
        return {"failure": "timeout"}
    except Exception:
        return {"failure": "error"}


async def collect_source_attribution(text, queries, source_url=None, *, search_results=None,
                                     max_sources=MAX_SOURCES):
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
    source_limit = max_sources if (isinstance(max_sources, int) and not isinstance(max_sources, bool)
                                   and 1 <= max_sources <= MAX_SOURCE_LIMIT) else MAX_SOURCES
    selected_urls = list(urls)[:source_limit] if candidates else []
    fetched = await asyncio.gather(*[_fetch_article(url) for url in selected_urls])
    failures = {"oversize": 0, "unsupported_content": 0, "timeout": 0,
                "blocked_or_unavailable": 0, "error": 0}
    matches, seen_matches = [], set()
    semantic_documents = []
    fetched_count = truncated_count = 0
    for requested_url, result in zip(selected_urls, fetched):
        if "failure" in result:
            failures[result["failure"]] += 1
            continue
        fetched_count += 1
        truncated_count += int(result["truncated"])
        semantic_documents.append({
            "url": result["url"], "title": result["title"] or urls[requested_url] or "Página consultada",
            "text": " ".join(result.get("sentences", []))[:12000],
            "truncated": bool(result.get("truncated")),
            "source_role": "submitted_source" if submitted in {requested_url, result["url"]}
                           else "retrieved_reference",
            "retrieved_at": result["retrieved_at"],
        })
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
        "fetch_attempt_count": len(selected_urls), "invalid_url_count": invalid_urls, "fetched_count": fetched_count,
        "failed_fetch_count": sum(failures.values()), "fetch_failure_counts": failures,
        "oversize_fetch_count": failures["oversize"], "source_text_truncated_count": truncated_count,
        "literal_segment_count": segment_count, "eligible_claim_count": eligible_count,
        "selected_claim_count": len(candidates), "omitted_claim_count": eligible_count - len(candidates),
        "matches_count": min(len(matches), MAX_MATCHES), "omitted_match_count": max(0, len(matches) - MAX_MATCHES),
    }
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
    return {"status": status, "decision_role": "source_attribution_only", "matches": matches[:MAX_MATCHES],
            "semantic_documents": semantic_documents,
            "reason": reason, "limitations": limitations, "coverage": coverage}
