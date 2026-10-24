"""Offline real-boundary simulation, not a measured factual-accuracy corpus."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core.openrouter_service import GeneratedText
from app.services.official_source_body import COPOM_INDEX_URL, CopomRecordReference, copom_detail_url
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import collect_official_copom_record, collect_source_attribution
from app.services.source_corroboration import corroborate_sources, is_original_record_claim, _passage_guard
from app.services.source_decision import apply_source_decision
from app.services.claim_policy import text_report


CLAIM = "Em 11 de maio de 2001, o Copom reduziu a Selic de 8,75% para 8,50% ao ano."
BODY = "O Copom decidiu, por unanimidade, elevar a taxa básica de juros em 0,25 ponto percentual, para 8,75% a.a."
REF = CopomRecordReference(123, "2001-05-11", "Comunicado consultado")
DETAIL_URL = copom_detail_url(REF)


def resource(url, rows):
    return FetchedResource(json.dumps({"conteudo": rows}).encode(), "application/json", url, "utf-8")


INDEX = resource(COPOM_INDEX_URL, [{"nro_reuniao": 123, "dataReferencia": "2001-05-11", "titulo": REF.title}])
DETAIL = resource(DETAIL_URL, [{"nro_reuniao": 123, "dataReferencia": "2001-05-11", "titulo": REF.title,
                               "textoComunicado": "<p>" + BODY + "</p>"}])


class OfficialCopomFlowTests(unittest.IsolatedAsyncioTestCase):
    async def read(self, text=CLAIM, cache=None, limit=3):
        cache = {} if cache is None else cache
        async def fetch(url, **_kwargs):
            return {COPOM_INDEX_URL: INDEX, DETAIL_URL: DETAIL}[url]
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_official_copom_record(text, cache, max_sources=limit)
        return result, cache, request

    async def test_two_public_requests_charged_no_synthetic_date_in_body(self):
        result, cache, request = await self.read()
        self.assertEqual(result["status"], "retrieved")
        self.assertEqual(result["new_fetch_count"], 2)
        self.assertEqual(len(cache), 2)
        self.assertEqual(request.await_count, 2)
        self.assertTrue(cache[COPOM_INDEX_URL]["discovery_only"])
        self.assertEqual(cache[DETAIL_URL]["sentences"][-1], BODY)
        self.assertIsNone(cache[DETAIL_URL]["publication_date"])
        for call in request.await_args_list:
            self.assertEqual(call.kwargs["max_redirects"], 0)
            self.assertEqual(call.kwargs["allowed_types"], {"application/json"})

    async def test_index_is_not_a_source_vote_or_body_document(self):
        _, cache, _ = await self.read()
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock()) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], include_documents=True,
                search_results=[{"link": url} for url in cache], fetched_cache=cache, max_sources=3)
        request.assert_not_awaited()
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["coverage"]["discovery_only_resource_count"], 1)
        self.assertEqual(len(result["_documents"]), 1)
        self.assertEqual(result["_documents"][0]["url"], DETAIL_URL)
        self.assertEqual(result["matches"], [])

    async def test_pipeline_retains_official_body_even_when_search_returns_no_url(self):
        from app.core.pipeline import _retrieve_source_attribution
        from app.core.serper_client import NewsSearch
        async def fetch(url, **_kwargs):
            return {COPOM_INDEX_URL: INDEX, DETAIL_URL: DETAIL}[url]
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_RESEARCH_ENABLED": "false",
                                     "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}), \
             patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch())) as search, \
             patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)) as request:
            result = await _retrieve_source_attribution(CLAIM, [CLAIM], None)
        self.assertEqual(result["coverage"]["official_record_recovery"]["status"], "retrieved")
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(request.await_count, 2)
        self.assertLessEqual(search.await_count, 3)
        self.assertEqual(len(result["_documents"]), 1)
        self.assertEqual(result["_documents"][0]["url"], DETAIL_URL)

    async def test_no_retries_refunds_or_over_budget_reads(self):
        for cache, limit in (({}, 1), ({"https://www.bbc.com/first": {"failure": "error"}}, 2)):
            result, _, request = await self.read(cache=cache, limit=limit)
            request.assert_not_awaited()
        _, cache, _ = await self.read()
        again, _, request = await self.read(cache=cache)
        self.assertEqual(again["status"], "already_attempted")
        request.assert_not_awaited()

    async def test_failed_request_stays_reserved(self):
        cache = {}
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=TimeoutError)) as request:
            result = await collect_official_copom_record(CLAIM, cache)
            second = await collect_official_copom_record(CLAIM, cache)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(cache[COPOM_INDEX_URL], {"failure": "timeout"})
        self.assertEqual(second["status"], "already_attempted")
        self.assertEqual(request.await_count, 1)

    async def test_cancelled_detail_is_not_refunded(self):
        cache = {}
        async def fetch(url, **_kwargs):
            if url == COPOM_INDEX_URL:
                return INDEX
            raise asyncio.CancelledError
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)):
            with self.assertRaises(asyncio.CancelledError):
                await collect_official_copom_record(CLAIM, cache)
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[DETAIL_URL], {"failure": "error"})

    async def test_nonmatching_date_does_not_use_latest_or_adjacent_meeting(self):
        result, cache, request = await self.read(CLAIM.replace("11 de maio", "12 de maio"))
        self.assertEqual(result["status"], "no_matching_record")
        self.assertEqual(request.await_count, 1)
        self.assertEqual(len(cache), 1)

    async def test_unrelated_future_or_qualified_claims_do_not_call_api(self):
        for claim in ("O PIB cresceu em 2001.", CLAIM + " Invista agora.",
                      CLAIM.replace("2001", "2099"), CLAIM.replace("Copom", "Banco Zeta")):
            result, _, request = await self.read(claim)
            self.assertEqual(result["status"], "not_requested")
            request.assert_not_awaited()

    async def comparison(self, doc, relation="refutes", claim=CLAIM):
        async def answer(prompt, **_kwargs):
            data = json.loads(prompt)
            claims = []
            for item in data["claims"]:
                reviews = []
                for source in data["sources"]:
                    passage = next((p for p in source["passages"] if p.get("official_record")), None)
                    reviews.append({"source_id": source["source_id"],
                        "assessment": "evidence" if passage else "insufficient",
                        "evidence": [{"excerpt_id": passage["excerpt_id"], "relation": relation}] if passage else []})
                claims.append({"claim_id": item["claim_id"], "source_reviews": reviews})
            return GeneratedText(json.dumps({"claims": claims}))
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=answer)) as model:
            result = await corroborate_sources(claim, [doc])
        return result, model

    async def test_exact_record_enters_comparison_and_final_attributed_decision(self):
        _, cache, _ = await self.read()
        doc = {**cache[DETAIL_URL], "source_role": "retrieved_reference"}
        result, model = await self.comparison(doc)
        model.assert_not_awaited()
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")
        self.assertTrue(result["coverage"]["complete_source_review"])
        self.assertTrue(all(provider["status"] == "not_requested" for provider in result["provider_coverage"].values()))
        self.assertEqual(result["state"], "refuted")
        evidence = result["claims"][0]["evidence"][0]
        self.assertEqual(evidence["excerpt"], BODY)
        self.assertTrue(is_original_record_claim(CLAIM, evidence))
        self.assertEqual(evidence["record_publication_date"], "2001-05-11")
        final = apply_source_decision(CLAIM, text_report(CLAIM, []), result)
        self.assertEqual(final["veracity_status"], "refuted")
        self.assertTrue(final["original_record_only"])
        self.assertIn("não duas fontes independentes", final["summary"])
        self.assertIsNone(final["confidence"])
        self.assertEqual(final["policy_version"], "2026-10-24.1")

    async def test_wrong_model_relation_metadata_only_or_submitted_record_cannot_conclude(self):
        _, cache, _ = await self.read()
        doc = {**cache[DETAIL_URL], "source_role": "retrieved_reference"}
        for change in ({"official_record": None}, {"sentences": [REF.title], "sentence_roles": ["context"]},
                       {"source_role": "submitted_source"}, {"url": "https://www.bbc.com/copy"}):
            result, model = await self.comparison({**doc, **change})
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()
        # Exercise the ordinary model path's existing rejection of a wrong
        # relation separately from the complete deterministic record reading.
        with patch("app.services.source_corroboration.typed_review_matrix", return_value=None):
            result, model = await self.comparison(doc, relation="supports")
        model.assert_awaited_once()
        self.assertEqual(result["state"], "insufficient")

    async def test_record_date_tampering_context_denial_and_future_blocked(self):
        _, cache, _ = await self.read()
        doc = {**cache[DETAIL_URL], "source_role": "retrieved_reference"}
        result, _ = await self.comparison(doc)
        evidence = result["claims"][0]["evidence"][0]
        for field, value in (("record_id", "124"), ("record_reference_date", "2001-05-12"),
                             ("reference_date_semantics", "meeting_date")):
            changed = deepcopy(evidence)
            changed["official_record"][field] = value
            self.assertFalse(is_original_record_claim(CLAIM, changed))
        passage = {"quote": BODY, "context": "É falso que " + BODY, "official_record": evidence["official_record"]}
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", "2026-10-20T12:00:00+00:00"))
        self.assertIsNotNone(_passage_guard(CLAIM, {**passage, "context": BODY}, "refutes", "2000-01-01T00:00:00+00:00"))

    async def test_hypothetical_negated_or_prior_decision_context_cannot_be_dropped(self):
        _, cache, _ = await self.read()
        proof = cache[DETAIL_URL]["official_record"]
        for opening in ("Em cenário hipotético.", "Na reunião anterior, em 11 de abril de 2001.",
                        "Não ocorreu a decisão a seguir.", "Talvez o cenário resulte na seguinte decisão.",
                        "Se a situação mudar, uma decisão seria esta:", "Este é um texto simulado."):
            passage = {"quote": BODY, "context": opening + " " + BODY, "official_record": proof}
            self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", "2026-10-20T12:00:00+00:00"), opening)
        # Actual decision may be followed by a separate outlook, not a
        # condition governing whether that completed formal act occurred.
        passage = {"quote": BODY, "context": BODY + " Os ajustes futuros serão ditados pela inflação.",
                   "official_record": proof}
        self.assertIsNone(_passage_guard(CLAIM, passage, "refutes", "2026-10-20T12:00:00+00:00"))
        for suffix in ("Essa decisão não ocorreu.", "Esta decisão talvez tenha ocorrido.",
                       "Aquela decisão nunca foi tomada.", "Essa decisão é hipotética."):
            passage["context"] = BODY + " " + suffix
            self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", "2026-10-20T12:00:00+00:00"))


if __name__ == "__main__":
    unittest.main()
