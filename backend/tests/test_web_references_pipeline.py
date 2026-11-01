import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core.pipeline import run_pipeline, _retrieve_source_attribution
from app.core.serper_client import NewsSearch, WEB_ENDPOINT, search_web


class WebSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_does_not_send_request(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": ""}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertEqual((await search_web("Uma frase literal suficientemente longa.")).status, "not_configured")
        post.assert_not_awaited()

    async def test_oversize_literal_is_not_cut_or_sent(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertEqual((await search_web("Não " + "palavra " * 100)).status, "not_requested")
        post.assert_not_awaited()

    async def test_only_safe_candidate_links_returned_with_preview_fields(self):
        payload = {"organic": [
            {"link": "https://example.com/article", "title": "Fonte", "snippet": "Falso snippet"},
            {"link": "javascript:alert(1)"}, {"link": "https://user:secret@example.com"},
            {"link": "https://example.com:444/article"}, {"link": "https://example.com:bad/article"},
        ]}
        sentence = "O Dr. Silva não anunciou a medida em 09/10/2026."
        with patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=payload))) as post:
            result = await search_web(sentence)
        self.assertEqual(result, [{"title": "Fonte", "link": "https://example.com/article",
                                   "snippet": "Falso snippet", "date": None, "source": ""}])
        self.assertEqual(post.call_args.args[0], WEB_ENDPOINT)
        self.assertEqual(post.call_args.kwargs["json"]["q"], sentence)
        self.assertEqual(post.call_args.kwargs["json"]["num"], 5)

    async def test_errors_and_empty_results_are_distinct(self):
        for code, payload, state in ((429, {}, "rate_limited"), (402, {}, "rate_limited"),
                                      (403, {}, "error"), (200, {}, "no_results"),
                                      (200, {"organic": {}}, "error")):
            with self.subTest(code=code, payload=payload), patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(code, json=payload))):
                self.assertEqual((await search_web("Uma frase completa para esta consulta.")).status, state)


class ReferencePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, text, attribution, hints=None):
        with patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=hints or [])), \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])) as facts, \
             patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})), \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])), \
             patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch(status="no_results"))), \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)):
            result = await run_pipeline(text)
        return result["report"], facts

    async def test_reference_is_not_a_truth_vote(self):
        sentence = "Elizabeth II morreu em 8 de setembro de 2022."
        attribution = {"status": "found", "decision_role": "source_attribution_only", "coverage": {},
                       "matches": [{"url": "https://example.com/article", "title": "Fonte", "claim": sentence,
                                    "excerpt": sentence, "match_method": "literal_sentence",
                                    "source_role": "retrieved_reference"}], "limitations": []}
        report, _ = await self.run_control(sentence, attribution)
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["score"], 50)
        self.assertEqual(report["source_attribution"]["status"], attribution["status"])
        self.assertEqual(report["source_attribution"]["matches"], attribution["matches"])
        self.assertEqual(report["source_attribution"]["decision_role"], "source_attribution_only")
        self.assertEqual(report["provider_coverage"]["web_references"]["decision_role"], "source_attribution_only")
        self.assertNotIn("evidence_strength", report)
        self.assertNotIn("source_corroboration", report)

    async def test_literal_hint_is_bounded_and_never_becomes_a_checked_claim(self):
        text = "Título. Autor. Atualização. Contexto. Não é verdade que a vacina altera o DNA."
        hint = "a vacina altera o DNA"
        attribution = {"status": "no_results", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": []}
        report, facts = await self.run_control(text, attribution, [hint])
        sent = [call.args[0] for call in facts.await_args_list]
        self.assertEqual(sent[0], hint)
        self.assertIn(text, sent)
        self.assertLessEqual(len(sent), 5)
        plan = report["provider_coverage"]["google_fact_check"]["query_plan"]
        self.assertEqual(plan["selected_count"], len(sent))
        self.assertEqual(plan["query_methods"][0], "extracted_literal_claim")
        self.assertTrue(plan["whole_text_queried"])
        self.assertEqual(report["claims"], ["Título.", "Autor.", "Atualização.", "Contexto.",
                                            "Não é verdade que a vacina altera o DNA."])
        self.assertEqual(report["search_claims"], [hint])
        self.assertEqual(report["search_claims_decision_role"], "search_hints_only")

    async def test_reference_failure_does_not_abort_or_leak_exception(self):
        attribution = {"status": "error", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": [], "reason": "Consulta não concluída."}
        report, _ = await self.run_control("Uma mensagem factual suficientemente longa.", attribution)
        self.assertEqual(report["provider_coverage"]["web_references"]["status"], "error")
        self.assertEqual(report["analysis_status"], "inconclusive")


class BoundedSourceRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_literal_search_and_one_attribution_read(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        leads = NewsSearch([{"link": "https://www.bbc.com/example"}])
        attribution = {"status": "no_results", "coverage": {}, "matches": []}
        with patch("app.core.pipeline.search_web", new=AsyncMock(return_value=leads)) as search, \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect:
            result = await _retrieve_source_attribution(text, [text], None)
        search.assert_awaited_once_with(text)
        collect.assert_awaited_once()
        self.assertEqual(collect.await_args.kwargs["search_results"], leads)
        self.assertNotIn("include_documents", collect.await_args.kwargs)
        self.assertEqual(result["coverage"]["max_search_queries"], 1)
        self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 20)
        self.assertEqual(result["coverage"]["search_queries"],
                         [{"method": "whole_literal_claim", "status": "success"}])

    async def test_invalid_or_missing_queries_do_not_send_a_search(self):
        for queries in ([], ["", "   "], ["x" * 501]):
            with self.subTest(queries=queries), \
                 patch("app.core.pipeline.search_web", new=AsyncMock()) as search, \
                 patch("app.core.pipeline.collect_source_attribution",
                       new=AsyncMock(return_value={"status": "no_results", "coverage": {}})) as collect:
                result = await _retrieve_source_attribution("Texto.", queries, None)
            search.assert_not_awaited()
            self.assertEqual(collect.await_args.kwargs["search_results"].status, "no_results")
            self.assertEqual(result["coverage"]["search_queries"], [])

    async def test_search_failure_is_sanitized_and_not_retried(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        with patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=RuntimeError("private-marker"))) as search, \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock()) as collect:
            result = await _retrieve_source_attribution(text, [text], None)
        search.assert_awaited_once_with(text)
        collect.assert_not_awaited()
        self.assertEqual(result["status"], "error")
        self.assertNotIn("private-marker", str(result))

    async def test_attribution_failure_is_sanitized(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        with patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch())), \
             patch("app.core.pipeline.collect_source_attribution",
                   new=AsyncMock(side_effect=RuntimeError("private-marker"))):
            result = await _retrieve_source_attribution(text, [text], None)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("private-marker", str(result))
