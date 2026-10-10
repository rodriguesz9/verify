"""Literal statements found in bounded public pages, never votes on truth.

Search titles/snippets identify retrieval leads only. A match requires the full
literal input sentence in fetched visible article text. Source repetition does
not establish accuracy, independence, authorship or agreement with the article.
"""
import asyncio
from datetime import datetime, timezone
import re

from bs4 import BeautifulSoup
from fastapi import HTTPException
import httpx

from app.services.claim_policy import input_claims, normalize_claim
from app.services.public_fetch import fetch_public_resource

ATTRIBUTION_VERSION = "literal_source_attribution_v1"
MAX_SOURCES = 3
MAX_MATCHES = 3
MAX_INPUT_SEGMENTS = 8
MAX_CLAIM_CHARACTERS = 1000
MAX_SOURCE_CHARACTERS = 50000
MAX_SOURCE_BYTES = 512 * 1024
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


def _article_sentences(resource):
    try:
        document = resource.data.decode(resource.encoding, errors="replace")
    except LookupError:
        document = resource.data.decode("utf-8", errors="replace")
    title = ""
    if resource.content_type == "text/plain":
        text = re.sub(r"\s+", " ", document).strip()
    else:
        soup = BeautifulSoup(document, "html.parser")
        title = soup.title.get_text(" ", strip=True)[:300] if soup.title else ""
        for tag in list(soup.find_all(True)):
            if tag.attrs is None:
                continue
            identifiers = " ".join([str(tag.get("id", "")), *tag.get("class", [])])
            if (tag.name in {"script", "style", "nav", "footer", "aside", "form", "template",
                             "noscript", "head", "dialog", "button", "input", "select", "textarea"}
                    or tag.has_attr("hidden")
                    or str(tag.get("aria-hidden", "")).lower() == "true"
                    or str(tag.get("role", "")).lower() == "dialog"
                    or _HIDDEN_STYLE.search(str(tag.get("style", "")))
                    or _CONSENT_UI.search(identifiers)):
                tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        # Keep neighboring block text in the same sentence until punctuation.
        # A preamble such as "Falso que:" must not disappear at a block boundary.
        text = re.sub(r"\s+", " ", main.get_text(" ", strip=True)).strip()
    truncated = len(text) > MAX_SOURCE_CHARACTERS
    sentences = input_claims(text[:MAX_SOURCE_CHARACTERS])
    if truncated and sentences:
        # The cut can precede a decisive qualifier; its last segment cannot match.
        sentences.pop()
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
        sentences, title, truncated = _article_sentences(resource)
        return {"url": final_url, "sentences": sentences, "title": title, "truncated": truncated,
                "retrieved_at": datetime.now(timezone.utc).isoformat()}
    except HTTPException as exc:
        return {"failure": {413: "oversize", 415: "unsupported_content", 504: "timeout"}.get(
            exc.status_code, "blocked_or_unavailable")}
    except (TimeoutError, httpx.TimeoutException):
        return {"failure": "timeout"}
    except Exception:
        return {"failure": "error"}


async def collect_source_attribution(text, queries, source_url=None, *, search_results=None):
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
    selected_urls = list(urls)[:MAX_SOURCES] if candidates else []
    fetched = await asyncio.gather(*[_fetch_article(url) for url in selected_urls])
    failures = {"oversize": 0, "unsupported_content": 0, "timeout": 0,
                "blocked_or_unavailable": 0, "error": 0}
    matches, seen_matches = [], set()
    fetched_count = truncated_count = 0
    for requested_url, result in zip(selected_urls, fetched):
        if "failure" in result:
            failures[result["failure"]] += 1
            continue
        fetched_count += 1
        truncated_count += int(result["truncated"])
        source_sentences = {}
        for sentence in result["sentences"]:
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
        "max_sources": MAX_SOURCES, "candidate_url_count": len(urls),
        "selected_url_count": len(selected_urls), "omitted_url_count": len(urls) - len(selected_urls),
        "invalid_url_count": invalid_urls, "fetched_count": fetched_count,
        "failed_fetch_count": sum(failures.values()), "fetch_failure_counts": failures,
        "oversize_fetch_count": failures["oversize"], "source_text_truncated_count": truncated_count,
        "literal_segment_count": segment_count, "eligible_claim_count": eligible_count,
        "selected_claim_count": len(candidates), "omitted_claim_count": eligible_count - len(candidates),
        "matches_count": min(len(matches), MAX_MATCHES), "omitted_match_count": max(0, len(matches) - MAX_MATCHES),
    }
    limitations = [
        "Trecho publicado na fonte consultada; isso não comprova verdade, autoria, endosso ou independência editorial.",
        "Comparação literal de até oito frases e três páginas; paráfrases e partes não consultadas podem ficar sem correspondência.",
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
            "reason": reason, "limitations": limitations, "coverage": coverage}
