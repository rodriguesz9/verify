import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core.pipeline import run_pipeline, _retrieve_source_attribution, SOURCE_SITE_FILTER, _source_recovery_query, _source_recovery_queries
from app.core.serper_client import NewsSearch, WEB_ENDPOINT, search_web


class WebSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_does_not_send_request(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": ""}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertEqual((await search_web("Uma frase literal suficientemente longa.")).status, "not_configured")
        post.assert_not_awaited()

    async def test_oversize_literal_is_not_cut_or_sent(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertEqual((await search_web("Não " + "palavra " * 100)).status, "no_results")
        post.assert_not_awaited()

    async def test_only_safe_candidate_links_returned_no_snippet_evidence(self):
        payload = {"organic": [
            {"link": "https://example.com/article", "title": "Fonte", "snippet": "Falso snippet"},
            {"link": "javascript:alert(1)"}, {"link": "https://user:secret@example.com"},
            {"link": "https://example.com:444/article"}, {"link": "https://example.com:bad/article"},
        ]}
        sentence = "O Dr. Silva não anunciou a medida em 09/10/2026."
        with patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=payload))) as post:
            result = await search_web(sentence)
        self.assertEqual(result, [{"title": "Fonte", "link": "https://example.com/article"}])
        self.assertEqual(post.call_args.args[0], WEB_ENDPOINT)
        self.assertEqual(post.call_args.kwargs["json"]["q"], sentence)
        self.assertEqual(post.call_args.kwargs["json"]["num"], 10)

    async def test_errors_and_empty_results_are_distinct(self):
        for code, payload, state in ((429, {}, "rate_limited"), (402, {}, "rate_limited"),
                                      (403, {}, "error"), (200, {}, "no_results"),
                                      (200, {"organic": {}}, "error")):
            with self.subTest(code=code, payload=payload), patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(code, json=payload))):
                self.assertEqual((await search_web("Uma frase completa para esta consulta.")).status, state)


class ReferencePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, text, attribution, hints=None):
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_SEARCH_LIMIT": "2"}), \
             patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=hints or [])), \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])) as facts, \
             patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})), \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])), \
             patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch(status="no_results"))) as web, \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)):
            result = await run_pipeline(text)
        return result["report"], facts, web

    async def test_reference_is_not_a_truth_vote(self):
        sentence = "Elizabeth II morreu em 8 de setembro de 2022."
        attribution = {"status": "found", "decision_role": "source_attribution_only", "coverage": {},
                       "matches": [{"url": "https://example.com/article", "title": "Fonte", "claim": sentence,
                                    "excerpt": sentence, "match_method": "literal_sentence",
                                    "source_role": "retrieved_reference"}], "limitations": []}
        report, _, web = await self.run_control(sentence, attribution)
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["score"], 50)
        self.assertEqual(report["source_attribution"], {key: value for key, value in attribution.items() if key != "_documents"})
        self.assertEqual(report["provider_coverage"]["web_references"]["decision_role"], "source_attribution_only")
        self.assertEqual([call.args[0] for call in web.await_args_list], [sentence, _source_recovery_query(sentence)[0]])

    async def test_query_selection_preserves_enclosing_negation_and_audit(self):
        text = "Título. Autor. Atualização. Contexto. Não é verdade que a vacina altera o DNA."
        attribution = {"status": "no_results", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": []}
        report, facts, _ = await self.run_control(text, attribution, ["a vacina altera o DNA"])
        sent = [call.args[0] for call in facts.await_args_list]
        self.assertEqual(sent[0], "Não é verdade que a vacina altera o DNA.")
        self.assertIn(text, sent)
        self.assertNotIn("a vacina altera o DNA", sent)
        self.assertLessEqual(len(sent), 5)
        self.assertEqual(report["provider_coverage"]["google_fact_check"]["query_plan"]["selected_count"], len(sent))
        self.assertEqual(report["claims"], ["Título.", "Autor.", "Atualização.", "Contexto.", "Não é verdade que a vacina altera o DNA."])

    async def test_reference_failure_does_not_abort_or_leak_exception(self):
        attribution = {"status": "error", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": [], "reason": "Consulta não concluída."}
        report, _, _ = await self.run_control("Uma mensagem factual suficientemente longa.", attribution)
        self.assertEqual(report["provider_coverage"]["web_references"]["status"], "error")
        self.assertEqual(report["analysis_status"], "inconclusive")


class CuratedSourceSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicitly_disabled_crosscheck_keeps_legacy_search_and_deadline(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "2"}),
              patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch())) as search,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value={"status": "no_results", "coverage": {}})) as collect):
            result = await _retrieve_source_attribution(text, [text], None, use_source_crosscheck=False)
        search.assert_awaited_once_with(text)
        self.assertFalse(collect.await_args.kwargs["include_documents"])
        self.assertEqual(result["coverage"]["max_search_queries"], 1)
        self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 20)

    async def retrieve(self, query, leads, extra=None, limit="2", documents=None):
        attribution = {"status": "no_results", "coverage": {}, "matches": [], "_documents": documents or []}
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": limit}),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[leads, extra or NewsSearch()])) as search,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect):
            result = await _retrieve_source_attribution(query, [query], None)
        return result, search, collect

    async def test_second_search_preserves_literal_negative_claim_and_is_bounded(self):
        text = "Elizabeth II não morreu em 9 de setembro de 2022."
        result, search, collect = await self.retrieve(text, NewsSearch([{"link": "https://wikipedia.org/example"}]),
            NewsSearch([{"link": "https://www.bbc.com/example"}]))
        self.assertEqual([call.args[0] for call in search.await_args_list], [text, _source_recovery_query(text)[0]])
        self.assertEqual(len(collect.await_args.kwargs["search_results"]), 2)
        self.assertEqual(len(result["coverage"]["search_queries"]), 2)
        self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 45)
        self.assertEqual(collect.await_args.kwargs["max_sources"], 6)

    def test_named_event_recovery_is_a_neutral_lead_not_a_rewritten_claim(self):
        for text, name, event in (("Elizabeth II morreu em 9 de setembro de 2022.", "Elizabeth II", "death"),
                                  ("A missão Apollo 11 foi lançada em 16 de julho de 1969.", "Apollo 11", "launch")):
            query, method = _source_recovery_query(text)
            self.assertIn(f'"{name}"', query)
            self.assertIn(event, query)
            self.assertEqual(method, "literal_identity_event_anchors")
            self.assertLessEqual(len(query), 500)
        text = "O Dr. Silva não recebeu R$ 1.500,00 em 09/10/2026."
        query, method = _source_recovery_query(text)
        self.assertEqual(query, text + " " + SOURCE_SITE_FILTER)
        self.assertEqual(method, "whole_literal_claim_curated_sites")

    def test_unknown_or_competing_event_recovery_preserves_complete_literal(self):
        text = "Elizabeth II nasceu em 1926 e morreu em 2022."
        self.assertEqual(_source_recovery_query(text)[0], text + " " + SOURCE_SITE_FILTER)

    def test_general_subject_uses_primary_and_editorial_search_without_rewriting(self):
        text = "O Instituto Alfa não registrou 42 ocorrências em 12/08/2021."
        plan = _source_recovery_queries(text, 3)
        self.assertEqual(len(plan), 2)
        self.assertTrue(all("Instituto Alfa" in query for query, _ in plan))
        self.assertTrue(all("42" not in query for query, _ in plan))
        self.assertIn("site:nasa.gov", plan[0][0])
        self.assertNotIn("site:science.nasa.gov", plan[0][0])
        self.assertIn("site:who.int", plan[0][0])
        self.assertIn("site:planalto.gov.br", plan[0][0])
        self.assertNotIn("site:nasa.gov", plan[1][0])
        self.assertNotIn("site:royal.uk", plan[1][0])
        self.assertEqual(plan[0][1], "literal_topic_anchors_primary_sources")
        self.assertEqual(_source_recovery_queries(text, 2), [_source_recovery_query(text)])

    async def test_general_subject_third_search_respects_quota_and_page_ceiling(self):
        text = "O Instituto Alfa não registrou 42 ocorrências em 12/08/2021."
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[NewsSearch(), NewsSearch(status="rate_limited")])) as search,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value={"status": "no_results", "coverage": {}, "_documents": []})) as collect):
            result = await _retrieve_source_attribution(text, [text], None)
        self.assertEqual(search.await_count, 2)
        self.assertEqual(search.await_args.args[0], _source_recovery_queries(text, 3)[0][0])
        self.assertEqual(result["coverage"]["search_queries"][-1]["status"], "rate_limited")
        self.assertEqual(collect.await_args.kwargs["max_sources"], 6)

    async def test_failure_or_explicit_one_search_does_not_retry(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        for leads, limit in ((NewsSearch(status="rate_limited"), "2"), (NewsSearch(status="not_configured"), "2"),
                             (NewsSearch(status="error"), "2"), (NewsSearch(status="no_results"), "1")):
            _, search, _ = await self.retrieve(text, leads, limit=limit)
            search.assert_awaited_once_with(text)

    async def test_failed_recovery_preserves_only_completed_first_wave(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        initial = {"status": "found", "matches": [{"claim": text}], "coverage": {}, "limitations": [], "_documents": []}
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "2"}),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[NewsSearch(), TimeoutError()])),
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=initial)) as collect):
            result = await _retrieve_source_attribution(text, [text], None)
        self.assertEqual(result["matches"], [{"claim": text}])
        self.assertEqual(result["coverage"]["recovery_status"], "timeout_or_error")
        collect.assert_awaited_once()

    async def test_three_request_plan_partitions_primary_and_editorial_before_one_recovery_read(self):
        text = "Elizabeth II morreu em 9 de setembro de 2022."
        attribution = {"status": "no_results", "coverage": {}, "matches": [], "_documents": []}
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[NewsSearch(), NewsSearch(), NewsSearch()])) as search,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect):
            result = await _retrieve_source_attribution(text, [text], None)
        self.assertEqual([call.args[0] for call in search.await_args_list], [text, *[query for query, _ in _source_recovery_queries(text, 3)]])
        self.assertEqual(collect.await_count, 2)
        self.assertEqual(result["coverage"]["max_search_queries"], 3)
        self.assertEqual(collect.await_args.kwargs["max_sources"], 6)

    async def test_partitioned_search_stops_before_third_request_after_quota(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[NewsSearch(), NewsSearch(status="rate_limited")])) as search,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value={"status": "no_results", "coverage": {}, "_documents": []}))):
            result = await _retrieve_source_attribution(text, [text], None)
        self.assertEqual(search.await_count, 2)
        self.assertEqual(result["coverage"]["search_queries"][-1]["status"], "rate_limited")

    async def test_two_link_hosts_without_usable_bodies_still_trigger_bounded_recovery(self):
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        leads = NewsSearch([{"link": "https://g1.globo.com/a"}, {"link": "https://www.bbc.com/a"}])
        result, search, collect = await self.retrieve(text, leads)
        self.assertEqual(search.await_count, 2)
        self.assertEqual(collect.await_count, 2)
        self.assertEqual(result["coverage"]["usable_source_family_count"], 0)

    async def test_two_usable_body_families_skip_recovery_and_keep_three_document_ceiling(self):
        from test_source_corroboration import documents
        text = "Elizabeth II morreu em 8 de setembro de 2022."
        result, search, collect = await self.retrieve(text, NewsSearch(), documents=documents())
        search.assert_awaited_once_with(text)
        collect.assert_awaited_once()
        self.assertEqual(result["coverage"]["usable_source_family_count"], 2)
        self.assertLessEqual(len(result["_documents"]), 3)

    async def test_qualified_query_too_long_is_omitted_not_cut(self):
        text = "Um contexto completo " + "x" * 430 + " não morreu em 9 de setembro de 2022."
        self.assertLessEqual(len(text), 500)
        _, search, _ = await self.retrieve(text, NewsSearch())
        search.assert_awaited_once_with(text)
