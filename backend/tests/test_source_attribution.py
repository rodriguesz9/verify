"""Mocked document attribution controls; no accuracy or independence claims."""
import asyncio
from datetime import datetime
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _article_sentences, collect_source_attribution

CLAIM = "A Dra. Ávila não recebeu R$ 1.500,00 em 14/10/2026."


class SearchResults(list):
    def __init__(self, items=(), status="success", reason=None):
        super().__init__(items)
        self.status, self.reason = status, reason


def page(text=CLAIM, *, url="https://example.test/final", content_type="text/html", encoding="utf-8"):
    data = text if content_type == "text/plain" else f"<html><head><title>Página de controle</title></head><body><article><p>{text}</p></article></body></html>"
    return FetchedResource(data.encode(), content_type, url, encoding)


class SourceAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovery_reuses_failures_and_bodies_with_six_total_fetch_attempts(self):
        urls = [f"https://example.test/article-{i}" for i in range(8)]
        cache = {}
        async def fetch(url, **kwargs):
            if url == urls[0]:
                raise HTTPException(403, "Blocked control")
            return page(url=url)
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)) as request:
            initial = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(
                [{"link": url} for url in urls[:3]]), include_documents=True, fetched_cache=cache)
            recovered = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(
                [{"link": url} for url in urls]), include_documents=True, fetched_cache=cache, max_sources=6)
        self.assertEqual(initial["coverage"]["new_fetch_count"], 3)
        self.assertEqual(recovered["coverage"]["new_fetch_count"], 3)
        self.assertEqual(recovered["coverage"]["reused_fetch_count"], 3)
        self.assertEqual(recovered["coverage"]["selected_url_count"], 6)
        self.assertEqual(recovered["coverage"]["failed_fetch_count"], 1)
        self.assertEqual(request.await_count, 6)
        self.assertEqual(len(cache), 6)
        self.assertEqual([call.args[0] for call in request.await_args_list].count(urls[0]), 1)

    async def test_changed_recovery_leads_do_not_reset_six_page_ceiling(self):
        cache = {}
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=page())) as request:
            await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(
                [{"link": f"https://example.test/old-{i}"} for i in range(3)]),
                include_documents=True, fetched_cache=cache)
            recovered = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(
                [{"link": f"https://example.test/new-{i}"} for i in range(6)]),
                include_documents=True, fetched_cache=cache, max_sources=6)
        self.assertEqual(request.await_count, 6)
        self.assertEqual(recovered["coverage"]["new_fetch_count"], 3)
        self.assertEqual(recovered["coverage"]["cumulative_fetch_attempt_count"], 6)

    def test_article_body_paragraphs_do_not_merge_headline_byline_or_publication_date(self):
        body = "Elizabeth II morreu em 8 de setembro de 2022."
        html = f'''<main><article><h1>Elizabeth II morreu em 9 de setembro de 2022.</h1>
            <div class="byline">Por Reuters</div>
            <p class="publication-date">Publicado em 09/09/2022</p>
            <section itemprop="articleBody"><p>{body}</p>
            <p>O reinado terminou depois de sete décadas.</p></section></article></main>'''
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        sentences, _, truncated, roles = _article_parts(resource)
        self.assertFalse(truncated)
        self.assertEqual(roles, ["context", "context", "body", "body"])
        self.assertEqual(sentences[2], body)
        self.assertEqual(sentences[1], "Por Reuters")
        self.assertNotIn("Publicado", " ".join(sentences))
        self.assertNotIn("09/09/2022", " ".join(sentences))

    def test_video_fallback_and_metadata_table_do_not_merge_with_body_event_date(self):
        body = "On July 16, 1969, the Saturn V rocket launches on the Apollo 11 mission."
        markup = f'<article><h1>Mission launch</h1><video><p>Enable JavaScript to view this video</p></video><div>July 10, 2018</div><table><tr><th>Historical Date</th><td>July 16, 1969</td></tr></table><p>{body}</p></article>'
        sentences, _, _, roles = _article_parts(FetchedResource(markup.encode(), "text/html", "https://example.test/resource", "utf-8"))
        index = sentences.index(body)
        self.assertEqual(roles[index], "body")
        self.assertNotIn("Enable JavaScript", " ".join(sentences))
        self.assertEqual(roles[sentences.index("Historical DateJuly 16, 1969")], "context")

    async def test_article_heading_is_context_not_a_body_match(self):
        html = f"<article><h1>{CLAIM}</h1><p>A página trata de assunto distinto.</p></article>"
        result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual(result["matches"], [])

    async def test_visible_heading_in_nonheading_tag_is_still_context_only(self):
        for kind in ("headline", "article-title", "subtitle", "content-head__title"):
            with self.subTest(kind=kind):
                html = f'<article><div class="{kind}">{CLAIM}</div><p>A página trata de assunto distinto.</p></article>'
                result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
                self.assertEqual(result["matches"], [])

    async def test_article_body_is_not_json_ld_or_search_metadata(self):
        html = f'''<head><title>{CLAIM}</title><meta name="description" content="{CLAIM}"></head>
            <body><article><script type="application/ld+json">{{"articleBody":"{CLAIM}"}}</script>
            <section itemprop="articleBody"><p>Texto sobre assunto distinto.</p></section></article></body>'''
        result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual(result["matches"], [])

    def test_rich_article_is_selected_instead_of_outer_main_or_teaser(self):
        body = "Elizabeth II morreu em 8 de setembro de 2022."
        html = f'''<main><h1>Notícias de hoje</h1><p>Uma notícia diferente abre o portal.</p>
            <article><p>Um cartão de outra notícia.</p></article>
            <article><h1>Um título que não é o corpo.</h1><p>{body}</p>
            <p>O monarca seguinte foi o rei Charles III.</p></article>
            <section><p>Elizabeth II morreu em 9 de setembro de 2022.</p></section></main>'''
        sentences, _, _, roles = _article_parts(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual([sentence for sentence, role in zip(sentences, roles) if role == "body"],
                         [body, "O monarca seguinte foi o rei Charles III."])
        self.assertNotIn("outra notícia", " ".join(sentences))
        self.assertNotIn("9 de setembro", " ".join(sentences))

    async def test_caption_and_quoted_block_do_not_supply_body_evidence(self):
        for container in ("figcaption", "blockquote", "caption"):
            with self.subTest(container=container):
                html = f"<article><{container}>{CLAIM}</{container}><p>Outra afirmação ocupa o corpo.</p></article>"
                result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
                self.assertEqual(result["matches"], [])

    async def test_unfinished_denial_heading_never_exposes_body_fragment_as_proof(self):
        positive = CLAIM.replace("não recebeu", "recebeu")
        html = f"<article><h1>Falso que:</h1><p>{positive}</p><p>A checagem encontrou registros diferentes.</p></article>"
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        result, _ = await self.collect(resource, text=positive)
        sentences, _, _, roles = _article_parts(resource)
        self.assertEqual(result["matches"], [])
        self.assertEqual(sentences[:2], ["Falso que:", positive])
        self.assertEqual(roles[:2], ["context", "context"])

    async def test_denial_heading_and_wire_credit_outside_article_are_not_erased(self):
        positive = CLAIM.replace("não recebeu", "recebeu")
        html = f'<main><h1>Falso que:</h1><div class="byline">Por Reuters</div><article><p>{positive}</p></article></main>'
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        result, _ = await self.collect(resource, text=positive)
        sentences, _, _, roles = _article_parts(resource)
        self.assertEqual(result["matches"], [])
        self.assertEqual(sentences, ["Falso que:", "Por Reuters", positive])
        self.assertEqual(roles, ["context", "context", "context"])

    def test_no_sentence_punctuation_is_invented_at_a_paragraph_boundary(self):
        html = '<article><p>A afirmação é que:</p><p>Elizabeth II não morreu em setembro de 2022.</p></article>'
        sentences, _, _, roles = _article_parts(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual(sentences, ["A afirmação é que: Elizabeth II não morreu em setembro de 2022."])
        self.assertEqual(roles, ["body"])

    def test_body_inline_markup_keeps_date_and_punctuation_without_title_prefix(self):
        html = '<article><h1>Notícia</h1><p>Elizabeth <b>II</b> morreu em <time>8 de setembro de 2022</time>.</p></article>'
        sentences, _, _, roles = _article_parts(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual(sentences[1], "Elizabeth II morreu em 8 de setembro de 2022.")
        self.assertEqual(roles, ["context", "body"])

    async def test_inline_letter_and_number_markup_does_not_invent_word_or_quantity_boundaries(self):
        claim = "Elizabeth II recebeu R$ 1.500,00 no Castelo Balmoral durante 16 dias."
        html = '<article><p>Elizabeth <b>II</b> recebeu R$ 1.<span>500</span>,00 n<strong>o</strong> Castelo Balmoral durante 1<em>6</em> dias.</p></article>'
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        result, _ = await self.collect(resource, text=claim)
        self.assertEqual(result["matches"][0]["excerpt"], claim)

    def test_text_only_container_preserves_inline_whitespace_and_excludes_comments(self):
        html = '<main><div itemprop="articleBody">Elizabeth <b>II</b> morreu<br>em 8 de setembro de 20<span>22</span>.<!--Não morreu.--> O reinado teve 7<i>0</i> anos.</div></main>'
        sentences, _, _, roles = _article_parts(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"))
        self.assertEqual(sentences, ["Elizabeth II morreu em 8 de setembro de 2022.", "O reinado teve 70 anos."])
        self.assertEqual(roles, ["body", "body"])

    async def test_internal_document_roles_are_opt_in_and_wire_credit_is_context(self):
        html = f'<article><p itemprop="author">Por Associated Press</p><p>{CLAIM}</p></article>'
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=resource)):
            regular = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final")
            internal = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final", include_documents=True)
        self.assertNotIn("_documents", regular)
        self.assertNotIn("sentence_roles", json.dumps(regular))
        self.assertEqual(internal["_documents"][0]["sentence_roles"], ["context", "body"])
        self.assertEqual(regular["matches"][0]["excerpt"], CLAIM)

    def test_publication_metadata_cannot_supply_event_date(self):
        body = "A rainha Elizabeth II morreu no Castelo de Balmoral, na Escócia."
        for metadata in (
            '<time datetime="2022-09-09">Atualizado em 09/09/2022</time>',
            '<span itemprop="datePublished">09/09/2022</span>',
            '<p itemprop="dateModified">Atualizado em 09/09/2022</p>',
            '<p>Publicação: <time itemprop="datePublished">09/09/2022</time></p>',
        ):
            with self.subTest(metadata=metadata):
                resource = FetchedResource(f"<article>{metadata}<p>{body}</p></article>".encode(),
                                           "text/html", "https://example.test/final", "utf-8")
                sentences, _, _ = _article_sentences(resource)
                self.assertNotIn("09/09/2022", " ".join(sentences))
                self.assertIn(body, " ".join(sentences))

    def test_inline_time_is_preserved_when_it_is_the_narrated_event_date(self):
        resource = FetchedResource(
            b'<article><p>Elizabeth II morreu em <time datetime="2022-09-08">8 de setembro de 2022</time>.</p></article>',
            "text/html", "https://example.test/final", "utf-8")
        sentences, _, _ = _article_sentences(resource)
        self.assertEqual(len(sentences), 1)
        self.assertIn("Elizabeth II morreu em 8 de setembro de 2022", sentences[0])

    async def test_internal_documents_are_opt_in_and_not_search_snippets(self):
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=page())):
            regular = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final")
            internal = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final", include_documents=True)
        self.assertNotIn("_documents", regular)
        self.assertEqual(internal["_documents"][0]["sentences"], [CLAIM])
        self.assertEqual(internal["_documents"][0]["source_role"], "submitted_source")

    async def test_crosscheck_prioritizes_distinct_eligible_families_with_same_fetch_budget(self):
        urls = ["https://www.uol.com.br/a", "https://www.uol.com.br/b", "https://folha.uol.com.br/c",
                "https://www.bbc.com/article", "https://www.royal.uk/article"]
        async def fetch(url, **kwargs):
            return page(url=url)
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults([
                {"link": url} for url in urls]), include_documents=True)
        self.assertEqual([call.args[0] for call in request.await_args_list], [urls[4], urls[0], urls[3]])
        self.assertEqual(result["coverage"]["selected_url_count"], 3)
        self.assertEqual(len(result["_documents"]), 3)

    async def collect(self, resource, *, text=CLAIM, queries=None, source_url="https://example.test/final", search_results=None):
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=resource)) as fetch:
            result = await collect_source_attribution(text, [text] if queries is None else queries,
                                                      source_url, search_results=search_results)
        return result, fetch

    async def test_exact_sentence_uses_real_page_and_bounded_fetch(self):
        result, fetch = await self.collect(page())
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["decision_role"], "source_attribution_only")
        self.assertEqual(len(result["matches"]), 1)
        match = result["matches"][0]
        self.assertEqual(match["excerpt"], CLAIM)
        self.assertEqual(match["claim"], CLAIM)
        self.assertEqual(match["match_method"], "literal_sentence")
        self.assertEqual(match["source_role"], "submitted_source")
        self.assertIsNotNone(datetime.fromisoformat(match["retrieved_at"]).utcoffset())
        self.assertEqual(fetch.await_args.kwargs["max_bytes"], 2 * 1024 * 1024)
        self.assertEqual(fetch.await_args.kwargs["max_redirects"], 3)
        self.assertEqual(fetch.await_args.kwargs["total_timeout"], 8.0)
        self.assertEqual(fetch.await_args.kwargs["allowed_types"], {"text/html", "application/xhtml+xml", "text/plain"})
        self.assertNotIn("verdict", result)
        self.assertNotIn("score", result)

    async def test_one_megabyte_page_keeps_visible_claim_after_hidden_script_is_removed(self):
        html = f"<html><head><script>{'X' * (1024 * 1024)}</script></head><body><article><p>{CLAIM}</p></article></body></html>"
        resource = FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8")
        self.assertGreater(len(resource.data), 1024 * 1024)
        self.assertLess(len(resource.data), 2 * 1024 * 1024)
        result, _ = await self.collect(resource)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["matches"][0]["excerpt"], CLAIM)
        self.assertEqual(result["coverage"]["max_source_bytes"], 2 * 1024 * 1024)
        self.assertEqual(result["coverage"]["source_text_truncated_count"], 0)

    async def test_page_larger_than_two_megabytes_is_still_rejected(self):
        resource = FetchedResource(b"X" * (2 * 1024 * 1024 + 1), "text/plain", "https://example.test/final", "utf-8")
        result, _ = await self.collect(resource)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["coverage"]["max_source_bytes"], 2 * 1024 * 1024)
        self.assertEqual(result["coverage"]["oversize_fetch_count"], 1)

    async def test_date_negation_amount_identity_and_qualifiers_do_not_match(self):
        for changed in (CLAIM.replace("14/10/2026", "15/10/2026"), CLAIM.replace("não recebeu", "recebeu"),
                        CLAIM.replace("1.500,00", "150,00"), CLAIM.replace("Ávila", "Silva"),
                        CLAIM[:-1] + " segundo uma mensagem não confirmada.", "Outro assunto ocupa esta página."):
            with self.subTest(changed=changed):
                result, _ = await self.collect(page(changed))
                self.assertEqual(result["status"], "no_results")
                self.assertEqual(result["matches"], [])

    async def test_negating_preamble_and_block_boundary_cannot_expose_positive_fragment(self):
        positive = CLAIM.replace("não recebeu", "recebeu")
        for html in (f"<article><p>É falso que {positive}</p></article>",
                     f"<article><p>Falso que:</p><p>{positive}</p></article>",
                     f"<article><p>É falso que <strong>{positive}</strong></p></article>"):
            result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"),
                                           text=positive)
            self.assertEqual(result["matches"], [])

    async def test_snippet_title_metadata_and_hidden_cookie_or_boilerplate_are_not_evidence(self):
        parts = [f"<nav>{CLAIM}</nav>", f"<footer>{CLAIM}</footer>", f"<aside>{CLAIM}</aside>",
                 f"<form>{CLAIM}</form>", f"<p hidden>{CLAIM}</p>", f"<p aria-hidden='TRUE'>{CLAIM}</p>",
                 f"<p style='DISPLAY : none !important'>{CLAIM}</p>",
                 f"<div role='dialog'>{CLAIM}</div>", f"<div id='cookie-banner'>{CLAIM}</div>",
                 f"<script>{CLAIM}</script>", f"<template>{CLAIM}</template>"]
        for hidden in parts:
            with self.subTest(hidden=hidden[:35]):
                html = f"<head><title>{CLAIM}</title><meta name='description' content='{CLAIM}'></head><body>{hidden}<article><p>Texto sobre outro assunto.</p></article></body>"
                result, _ = await self.collect(FetchedResource(html.encode(), "text/html", "https://example.test/final", "utf-8"),
                                               source_url=None, search_results=SearchResults([
                                                   {"link": "https://example.test/final", "title": CLAIM, "snippet": CLAIM}]))
                self.assertEqual(result["matches"], [])

    async def test_only_title_or_snippet_cannot_match_when_body_is_unrelated(self):
        result, _ = await self.collect(page("A página trata de assunto distinto."), source_url=None,
                                      search_results=SearchResults([{"link": "https://example.test/final", "title": CLAIM,
                                                                    "snippet": CLAIM}]))
        self.assertEqual(result["status"], "no_results")

    async def test_plain_text_preserves_angle_brackets_and_unknown_encoding_fallback(self):
        text = "A Dra. Ávila não removeu <nao> nem <script> em 14/10/2026."
        result, _ = await self.collect(page(text, content_type="text/plain", encoding="unknown-codec"), text=text)
        self.assertEqual(result["matches"][0]["excerpt"], text)

    async def test_redirect_uses_final_url_and_retains_submitted_role(self):
        result, _ = await self.collect(page(url="https://example.test/redirect-final"), source_url="https://example.test/original#fragment")
        self.assertEqual(result["matches"][0]["url"], "https://example.test/redirect-final")
        self.assertEqual(result["matches"][0]["source_role"], "submitted_source")

    async def test_same_host_alone_does_not_make_reference_the_submitted_source(self):
        async def fetch(url, **kwargs):
            return page("A página não contém a afirmação enviada." if url.endswith("submitted") else CLAIM, url=url)
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)):
            result = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/submitted",
                                                      search_results=SearchResults([{"link": "https://example.test/other"}]))
        self.assertEqual(result["matches"][0]["source_role"], "retrieved_reference")

    async def test_url_budget_deduplicates_fragments_and_fetches_three_in_parallel(self):
        active = maximum = 0
        async def fetch(url, **kwargs):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0)
            active -= 1
            return page(url=url)
        items = [{"link": f"https://example.test/{number}"} for number in range(5)]
        items.insert(0, {"link": "https://example.test/submitted#fragment"})
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], "https://EXAMPLE.test/submitted", search_results=SearchResults(items))
        self.assertEqual(request.await_count, 3)
        self.assertEqual(maximum, 3)
        self.assertEqual(result["coverage"]["candidate_url_count"], 6)
        self.assertEqual(result["coverage"]["omitted_url_count"], 3)
        self.assertEqual(len(result["matches"]), 3)
        self.assertEqual(result["matches"][0]["source_role"], "submitted_source")

    async def test_multiple_redirects_to_one_page_are_not_duplicate_matches(self):
        result, _ = await self.collect(page(), source_url="https://example.test/final", search_results=SearchResults([
            {"link": "https://example.test/alias"}, {"link": "https://example.test/other-alias"}]))
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["coverage"]["fetched_count"], 3)

    async def test_candidate_budget_and_match_cap_are_explicit(self):
        claims = [f"A cidade {number} inaugurou uma ponte em 2024." for number in range(10)]
        text = " ".join(claims)
        result, _ = await self.collect(page(text), text=text, queries=[claims[-1]])
        self.assertEqual(result["matches"][0]["claim"], claims[-1])
        self.assertEqual(len(result["matches"]), 3)
        self.assertEqual(result["coverage"]["selected_claim_count"], 8)
        self.assertEqual(result["coverage"]["omitted_claim_count"], 2)
        self.assertEqual(result["coverage"]["omitted_match_count"], 5)

    async def test_nonliteral_short_and_oversize_claims_do_not_fetch(self):
        for text in ("Lua.", "Em 2026.", "A" * 1001 + " cidade abriu uma ponte."):
            result, fetch = await self.collect(page(), text=text)
            self.assertEqual(result["matches"], [])
            self.assertEqual(result["status"], "no_results")
            fetch.assert_not_awaited()
        negated = "Não é verdade que a cidade inaugurou uma ponte em 2024."
        result, _ = await self.collect(page("A cidade inaugurou uma ponte em 2024."), text=negated,
                                      queries=["A cidade inaugurou uma ponte em 2024."])
        self.assertEqual(result["matches"], [])

    async def test_truncated_last_segment_is_never_matched(self):
        text = "A cidade inaugurou uma ponte em 2024."
        padding = "X" * (50000 - len(text) - 1) + ". "
        resource = page(padding + text + " Mas a mensagem adiciona uma ressalva.", content_type="text/plain")
        result, _ = await self.collect(resource, text=text)
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["coverage"]["source_text_truncated_count"], 1)

    async def test_oversize_failed_fetch_and_search_status_are_sanitized(self):
        for status, failure in ((413, "oversize"), (415, "unsupported_content"), (504, "timeout"), (403, "blocked_or_unavailable")):
            with self.subTest(status=status), patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(
                    side_effect=HTTPException(status, "PRIVATE-SERVER-BODY"))):
                result = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final")
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["coverage"]["fetch_failure_counts"][failure], 1)
                self.assertNotIn("PRIVATE", json.dumps(result))
        for search_status, expected in (("not_configured", "not_configured"), ("no_results", "no_results"),
                                        ("error", "error"), ("timeout", "error"), ("rate_limited", "error")):
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(
                status=search_status, reason="PRIVATE-PROVIDER-BODY"))
            self.assertEqual(result["status"], expected)
            self.assertEqual(result["coverage"]["search_status"], search_status)
            self.assertNotIn("PRIVATE", json.dumps(result))
        result = await collect_source_attribution(CLAIM, [CLAIM], search_results=SearchResults(status={"bad": "status"}))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["coverage"]["search_status"], "invalid_response")

    async def test_partial_failure_does_not_discard_real_match(self):
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=[
                page(), RuntimeError("PRIVATE-ERROR")])):
            result = await collect_source_attribution(CLAIM, [CLAIM], "https://example.test/final", search_results=SearchResults([
                {"link": "https://example.test/unavailable"}], status="error", reason="PRIVATE-PROVIDER-BODY"))
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["coverage"]["fetched_count"], 1)
        self.assertEqual(result["coverage"]["failed_fetch_count"], 1)
        self.assertNotIn("PRIVATE", json.dumps(result))

    async def test_invalid_credential_urls_never_fetch(self):
        for url in ("javascript:alert(1)", "https://user:secret@example.test/x", "https://example.test:8080/x", "https://example.test/a b"):
            result, fetch = await self.collect(page(), source_url=url)
            fetch.assert_not_awaited()
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["coverage"]["invalid_url_count"], 1)


if __name__ == "__main__":
    unittest.main()
