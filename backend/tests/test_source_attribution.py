"""Mocked document attribution controls; no accuracy or independence claims."""
import asyncio
from datetime import datetime
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import collect_source_attribution

CLAIM = "A Dra. Ávila não recebeu R$ 1.500,00 em 14/10/2026."


class SearchResults(list):
    def __init__(self, items=(), status="success", reason=None):
        super().__init__(items)
        self.status, self.reason = status, reason


def page(text=CLAIM, *, url="https://example.test/final", content_type="text/html", encoding="utf-8"):
    data = text if content_type == "text/plain" else f"<html><head><title>Página de controle</title></head><body><article><p>{text}</p></article></body></html>"
    return FetchedResource(data.encode(), content_type, url, encoding)


class SourceAttributionTests(unittest.IsolatedAsyncioTestCase):
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
