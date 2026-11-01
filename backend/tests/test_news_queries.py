"""Offline literal news retrieval controls, not factual accuracy benchmarks."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from helpers import app  # isolated credentials before importing pipeline
from app.core.pipeline import run_pipeline
from app.core.serper_client import NEWS_ENDPOINT, NewsSearch, search_news
from app.services.factual_queries import build_fact_check_queries


class NewsQueryPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, text, hints=(), news=()):
        attribution = {"status": "no_results", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": []}
        with (patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}),
              patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=list(hints))),
              patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])) as facts,
              patch("app.core.pipeline.search_news", new=AsyncMock(return_value=NewsSearch(news))) as searches,
              patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})),
              patch("app.core.pipeline._retrieve_source_attribution", new=AsyncMock(return_value=attribution))):
            result = await run_pipeline(text)
        return result, searches, facts

    async def test_literal_hint_stays_bounded_while_complete_sentence_is_retained(self):
        sentence = "Não é verdade que a Dra. Ávila recebeu R$ 1.500,00 em 14/10/2026 hoje."
        text = sentence + " Outra afirmação."
        hint = "a Dra. Ávila recebeu"
        result, searches, _ = await self.run_control(text, [hint])
        queries = [call.args[0] for call in searches.await_args_list]
        self.assertEqual(queries, [hint, text, sentence])
        plan = result["report"]["provider_coverage"]["serper"]["query_plan"]
        self.assertEqual(plan["extracted_valid_count"], 1)
        self.assertEqual(plan["query_methods"][0], "extracted_literal_claim")
        self.assertTrue(plan["whole_text_queried"])
        self.assertFalse(plan["truncated"])

    async def test_unsupported_hint_never_becomes_query_or_checked_claim(self):
        text = "A avó não recebeu R$ 20 em 14/10/2026."
        invented = "A avó recebeu R$ 20 em 14/10/2026."
        result, searches, _ = await self.run_control(text, [invented])
        searches.assert_awaited_once_with(text)
        report = result["report"]
        self.assertEqual(report["claims"], [text])
        self.assertEqual(report["search_claims"], [invented])
        self.assertEqual(report["search_claims_decision_role"], "search_hints_only")
        self.assertEqual(report["provider_coverage"]["serper"]["query_plan"]["extracted_rejected_count"], 1)
        self.assertEqual(report["veracity_status"], "unverified")

    async def test_empty_hints_preserve_entire_input_past_200_characters(self):
        text = "Contexto documental " + "sobre a medida " * 15 + "não prevê R$ 1.500,00 em 14/10/2026."
        self.assertGreater(len(text), 200)
        self.assertLessEqual(len(text), 500)
        result, searches, _ = await self.run_control(text)
        searches.assert_awaited_once_with(text)
        self.assertTrue(result["report"]["provider_coverage"]["serper"]["query_plan"]["whole_text_queried"])

    async def test_duplicate_hints_keep_whole_input_within_three_query_budget(self):
        sentences = [f"A cidade {number} abriu uma ponte." for number in range(4)]
        text = " ".join(sentences)
        result, searches, _ = await self.run_control(text, [*sentences, sentences[0]])
        queries = [call.args[0] for call in searches.await_args_list]
        self.assertEqual(queries, [*sentences[:2], text])
        self.assertEqual(len(set(queries)), len(queries))
        plan = result["report"]["provider_coverage"]["serper"]["query_plan"]
        self.assertEqual(plan["limit"], 3)
        self.assertEqual(plan["max_query_chars"], 500)
        self.assertEqual(plan["selected_count"], searches.await_count)
        self.assertNotIn(text, json.dumps(plan))
        self.assertNotIn(sentences[0], json.dumps(plan))

    async def test_oversize_input_selects_complete_short_sentence_without_cutting(self):
        oversize = "Contexto " + "x" * 500 + " não recebeu R$ 20 em 14/10/2026."
        sentence = "A Dra. Ávila não recebeu R$ 20 em 14/10/2026."
        result, searches, _ = await self.run_control(oversize + "\n" + sentence, [oversize])
        searches.assert_awaited_once_with(sentence)
        plan = result["report"]["provider_coverage"]["serper"]["query_plan"]
        self.assertEqual(plan["oversize_candidate_count"], 2)
        self.assertFalse(plan["whole_text_queried"])
        self.assertFalse(plan["truncated"])

    async def test_existing_5000_fact_check_guard_remains_intact(self):
        oversize = "Contexto " + "x" * 5000 + " não recebeu R$ 20 em 14/10/2026."
        sentence = "A Dra. Ávila não recebeu R$ 20 em 14/10/2026."
        result, searches, facts = await self.run_control(oversize + "\n" + sentence, [oversize, sentence])
        facts.assert_awaited_once_with(sentence)
        searches.assert_awaited_once_with(sentence)
        fact_plan = result["report"]["provider_coverage"]["google_fact_check"]["query_plan"]
        self.assertEqual(fact_plan["max_query_chars"], 5000)
        self.assertEqual(fact_plan["oversize_candidate_count"], 2)
        self.assertFalse(fact_plan["truncated"])

    async def test_no_complete_query_fits_is_not_requested_and_never_sent(self):
        text = "Contexto " + "x" * 500 + " não prevê R$ 20 em 14/10/2026."
        result, searches, facts = await self.run_control(text)
        searches.assert_not_awaited()
        facts.assert_awaited_once_with(text)
        coverage = result["report"]["provider_coverage"]["serper"]
        self.assertEqual(coverage["status"], "not_requested")
        self.assertEqual(coverage["queries"], [])
        self.assertIn("500 caracteres", coverage["reason"])
        self.assertEqual(coverage["query_plan"]["selected_count"], 0)
        self.assertEqual(coverage["query_plan"]["oversize_candidate_count"], 1)
        self.assertFalse(coverage["query_plan"]["truncated"])
        self.assertEqual(result["report"]["veracity_status"], "unverified")

    async def test_topical_complete_context_never_votes_on_truth(self):
        text = "Elizabeth II morreu no Castelo Balmoral, localizado na Escócia, em 8 de setembro de 2022."
        hints = ["no Castelo Balmoral", "localizado na Escócia"]
        item = {"title": text, "snippet": "", "link": "https://example.org/news", "date": "2022-09-08"}
        result, searches, _ = await self.run_control(text, hints, [item])
        self.assertEqual([call.args[0] for call in searches.await_args_list], [*hints, text])
        self.assertEqual({key: value for key, value in result["serper_news"][0].items()
                          if key != "publisher_assessment"}, item)
        self.assertEqual(result["serper_news"][0]["publisher_assessment"]["level"], "unclassified")
        coverage = result["report"]["provider_coverage"]["serper"]
        self.assertEqual(coverage["status"], "success")
        self.assertEqual(coverage["decision_role"], "context_only")
        self.assertEqual(coverage["query_plan"]["decision_role"], "retrieval_only")
        self.assertEqual(result["report"]["veracity_status"], "unverified")


class NewsQueryClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_http_payload_preserves_500_character_literal_past_200(self):
        prefix = "Contexto documental "
        suffix = " não recebeu R$ 1.500,00 em 14/10/2026."
        sentence = prefix + "x" * (500 - len(prefix) - len(suffix)) + suffix
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"news": []})

        client = httpx.AsyncClient
        transport = httpx.MockTransport(respond)
        with (patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}),
              patch("app.core.serper_client.httpx.AsyncClient", side_effect=lambda **kwargs: client(transport=transport, **kwargs))):
            result = await search_news("  " + sentence + "  ")
        self.assertEqual(result.status, "no_results")
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), NEWS_ENDPOINT)
        self.assertEqual(json.loads(requests[0].content)["q"], sentence)
        self.assertTrue(json.loads(requests[0].content)["q"].endswith(suffix))

    async def test_invalid_and_oversize_queries_are_not_requested_before_http(self):
        for query in ("x" * 501, "", " \n ", None, 500, ["literal"]):
            with (self.subTest(query_type=type(query).__name__),
                  patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}),
                  patch("app.core.serper_client.httpx.AsyncClient") as client):
                result = await search_news(query)
                self.assertEqual(result.status, "not_requested")
                self.assertIn("500 caracteres", result.reason)
                client.assert_not_called()

    async def test_invalid_query_stays_not_requested_even_without_key(self):
        with (patch.dict(os.environ, {"SERPERAPI_KEY": ""}),
              patch("app.core.serper_client.httpx.AsyncClient") as client):
            self.assertEqual((await search_news("x" * 501)).status, "not_requested")
            self.assertEqual((await search_news("Uma frase completa.")).status, "not_configured")
        client.assert_not_called()


class NewsQueryLimitTests(unittest.TestCase):
    def test_default_5000_limit_preserved_and_news_limit_omits_whole_candidates(self):
        oversize = "Contexto " + "x" * 500 + " não prevê R$ 20 em 14/10/2026."
        sentence = "A Dra. Ávila não recebeu R$ 20 em 14/10/2026."
        text = oversize + "\n" + sentence
        default_queries, default_audit = build_fact_check_queries(text, [])
        news_queries, news_audit = build_fact_check_queries(text, [], limit=3, max_query_chars=500)
        self.assertIn(text, default_queries)
        self.assertEqual(default_audit["max_query_chars"], 5000)
        self.assertEqual(news_queries, [sentence])
        self.assertEqual(news_audit["max_query_chars"], 500)
        self.assertEqual(news_audit["oversize_candidate_count"], 2)
        self.assertFalse(news_audit["truncated"])

    def test_invalid_character_limits_are_rejected(self):
        for limit in (0, -1, 5001, True, 500.0, "500", None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                build_fact_check_queries("Uma frase completa.", [], max_query_chars=limit)


if __name__ == "__main__":
    unittest.main()
