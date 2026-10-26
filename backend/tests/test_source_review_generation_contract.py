"""Offline generation contracts through mocked HTTP, never model accuracy."""
import copy
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services import source_corroboration as sources


CLAIM = "A pesquisadora Zeta morreu em 12 de agosto de 2021."
QUOTES = ("A pesquisadora Zeta faleceu em 12 de agosto de 2021.",
          "A pesquisadora Zeta morreu em 12 de agosto de 2021.")


def documents():
    return [{"url": url, "title": "Controle inventado", "sentences": [quote],
             "retrieved_at": "2026-10-18T12:00:00+00:00", "truncated": False}
            for url, quote in zip(("https://www.bbc.com/controle", "https://www.royal.uk/controle"), QUOTES)]


def answer(request, insufficient=False):
    return {"claims": [{"claim_id": claim["claim_id"], "source_reviews": [
        {"source_id": source["source_id"], "assessment": "insufficient" if insufficient else "evidence",
         "evidence": [] if insufficient else [{"excerpt_id": source["passages"][0]["excerpt_id"],
                                               "relation": "supports"}]}
        for source in request["sources"]]} for claim in request["claims"]]}


class SourceReviewGenerationSchemaTests(unittest.TestCase):
    def test_maximum_matrix_has_exact_cardinalities_and_server_owned_id_enums(self):
        request = {"claims": [{"claim_id": f"c{i}", "claim": f"Controle {i}."} for i in range(1, 6)],
                   "sources": [{"source_id": f"s{i}", "passages": [
                       {"excerpt_id": f"s{i}:e1-2", "quote": f"Corpo literal {i}.",
                        "context": f"Qualificador preservado {i}.", "temporal_anchor": {"date": "2021-08-12"}}]}
                       for i in range(1, 4)]}
        before = copy.deepcopy(request)
        base_schema = copy.deepcopy(sources.SCHEMA)
        prompt, schema = sources._comparison_request(request)
        sent = json.loads(prompt)
        self.assertEqual(request, before)
        self.assertEqual(sources.SCHEMA, base_schema)
        self.assertEqual(sent["sources"], before["sources"])
        self.assertEqual(sent["claims"], before["claims"])
        contract = sent["review_contract"]
        self.assertEqual(contract["expected_source_pair_count"], 15)
        self.assertEqual(contract["required_source_reviews"], [
            {"claim_id": f"c{i}", "source_ids": ["s1", "s2", "s3"]} for i in range(1, 6)])
        # Contract names work to perform; it supplies no guessed assessment.
        self.assertNotIn("assessment", json.dumps(contract))
        claims = schema["properties"]["claims"]
        self.assertEqual((claims["minItems"], claims["maxItems"]), (5, 5))
        self.assertEqual(claims["items"]["properties"]["claim_id"]["enum"], [f"c{i}" for i in range(1, 6)])
        reviews = claims["items"]["properties"]["source_reviews"]
        self.assertEqual((reviews["minItems"], reviews["maxItems"]), (3, 3))
        self.assertEqual(reviews["items"]["properties"]["source_id"]["enum"], ["s1", "s2", "s3"])
        evidence = reviews["items"]["properties"]["evidence"]
        self.assertEqual(evidence["maxItems"], 6)
        self.assertEqual(evidence["items"]["properties"]["excerpt_id"]["enum"], [f"s{i}:e1-2" for i in range(1, 4)])
        self.assertNotIn("quote", evidence["items"]["properties"])

    def test_sequential_requests_do_not_leak_previous_ids_or_counts(self):
        def request(count):
            return {"claims": [{"claim_id": f"c{count}", "claim": "Controle."}],
                    "sources": [{"source_id": f"s{i}", "passages": [{"excerpt_id": f"s{i}:e{count}",
                                  "quote": "Corpo literal."}]} for i in range(1, count + 1)]}
        _, first = sources._comparison_request(request(3))
        _, second = sources._comparison_request(request(1))
        reviews = second["properties"]["claims"]["items"]["properties"]["source_reviews"]
        self.assertEqual(reviews["maxItems"], 1)
        self.assertEqual(reviews["items"]["properties"]["source_id"]["enum"], ["s1"])
        self.assertNotIn("s3", json.dumps(second))
        self.assertIn("s3", json.dumps(first))


class SourceReviewGenerationTransportTests(unittest.IsolatedAsyncioTestCase):
    async def run_http(self, provider="openrouter", *, mutate=None, insufficient=False, finish_reason="stop", text=CLAIM):
        sent = []
        client_type = httpx.AsyncClient

        async def respond(request):
            payload = json.loads(request.content)
            if request.url.host == "openrouter.ai":
                prompt = payload["messages"][-1]["content"]
                schema = payload["response_format"]["json_schema"]["schema"]
                self.assertTrue(payload["response_format"]["json_schema"]["strict"])
                self.assertEqual(payload["model"], "openrouter/free")
                self.assertTrue(all(value == 0 for value in payload["provider"]["max_price"].values()))
            else:
                self.assertEqual(request.url.host, "generativelanguage.googleapis.com")
                prompt = payload["contents"][0]["parts"][0]["text"]
                schema = payload["generationConfig"]["responseSchema"]
            prepared = json.loads(prompt)
            sent.append({"provider": request.url.host, "request": prepared, "schema": schema})
            value = answer(prepared, insufficient)
            if mutate:
                mutate(value, prepared)
            raw = json.dumps(value, ensure_ascii=False)
            if request.url.host == "openrouter.ai":
                return httpx.Response(200, json={"model": "test/control:free", "choices": [
                    {"finish_reason": finish_reason, "message": {"content": raw}}], "usage": {"cost": 0}})
            return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
                "content": {"parts": [{"text": raw}]}}]})

        transport = httpx.MockTransport(respond)

        def client_factory(**kwargs):
            return client_type(transport=transport, **kwargs)

        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": provider,
                "OPENROUTER_ENABLED": "true", "OPENROUTER_API_KEY": "offline-fake-key", "OPENROUTER_MODEL": "openrouter/free",
                "OPENROUTER_FALLBACK_MODELS": "", "GEMINI_API_KEY": "offline-fake-key", "GEMINI_MODEL_NAME": "offline-control",
                "GEMINI_FALLBACK_MODELS": ""}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(sources.openrouter_service, "_reserve_request") as router_reservation, \
             patch.object(sources.gemini_client, "_reserve_request", new=AsyncMock()) as gemini_reservation, \
             patch("httpx.AsyncClient", side_effect=client_factory):
            result = await sources.corroborate_sources(text, documents())
        technical_failure = mutate is not None or provider == "openrouter" and finish_reason != "stop"
        self.assertEqual(len(sent), 2 if technical_failure else 1,
                         "Only a technical failure may use the existing alternate once.")
        (router_reservation if provider == "openrouter" else gemini_reservation).assert_called_once()
        alternate_reservation = gemini_reservation if provider == "openrouter" else router_reservation
        if technical_failure:
            alternate_reservation.assert_called_once()
            self.assertEqual(sent[0]["request"], sent[1]["request"])
        else:
            alternate_reservation.assert_not_called()
        return result, sent[0]

    async def test_both_rest_transports_receive_exact_matrix_and_keep_literal_body_values(self):
        for provider in ("openrouter", "gemini"):
            with self.subTest(provider=provider):
                result, sent = await self.run_http(provider)
                self.assertEqual(result["state"], "corroborated")
                self.assertEqual({entry["excerpt"] for entry in result["claims"][0]["evidence"]}, set(QUOTES))
                coverage = result["provider_coverage"][provider]
                self.assertTrue(coverage["complete_source_review"])
                self.assertEqual(coverage["reviewed_source_pair_count"], 2)
                claims = sent["schema"]["properties"]["claims"]
                reviews = claims["items"]["properties"]["source_reviews"]
                self.assertEqual((claims["minItems"], claims["maxItems"]), (1, 1))
                self.assertEqual((reviews["minItems"], reviews["maxItems"]), (2, 2))
                self.assertEqual(reviews["items"]["properties"]["source_id"]["enum"], ["s1", "s2"])
                self.assertEqual(sent["request"]["review_contract"]["expected_source_pair_count"], 2)

    async def test_complete_insufficient_matrix_remains_insufficient_without_extra_call(self):
        result, _ = await self.run_http(insufficient=True)
        self.assertEqual(result["state"], "insufficient")
        self.assertTrue(result["coverage"]["complete_source_review"])
        self.assertEqual(result["claims"][0]["evidence"], [])

    async def test_two_claims_and_two_sources_require_all_four_explicit_reviews(self):
        text = CLAIM + " A pesquisadora Zeta nasceu em 1 de maio de 1980."
        result, sent = await self.run_http(insufficient=True, text=text)
        self.assertEqual(result["state"], "insufficient")
        self.assertTrue(result["coverage"]["complete_source_review"])
        coverage = result["provider_coverage"]["openrouter"]
        self.assertEqual(coverage["expected_source_pair_count"], 4)
        self.assertEqual(coverage["reviewed_source_pair_count"], 4)
        self.assertEqual(sent["request"]["review_contract"]["required_source_reviews"], [
            {"claim_id": "c1", "source_ids": ["s1", "s2"]},
            {"claim_id": "c2", "source_ids": ["s1", "s2"]}])
        self.assertTrue(all(claim["evidence"] == [] for claim in result["claims"]))

    async def test_http200_missing_second_source_is_still_invalid_with_observed_count(self):
        def omit(value, request):
            value["claims"][0]["source_reviews"].pop()
        result, _ = await self.run_http(mutate=omit)
        self.assertEqual(result["status"], "invalid_response")
        self.assertEqual(result["provider_coverage"]["openrouter"]["reviewed_source_pair_count"], 1)
        self.assertFalse(result["coverage"]["complete_source_review"])
        self.assertEqual(result["claims"][0]["evidence"], [])

    async def test_duplicate_source_wrong_owner_and_sentence_id_never_pass_full_decoder(self):
        def duplicate(value, request):
            value["claims"][0]["source_reviews"][1]["source_id"] = "s1"

        def wrong_owner(value, request):
            value["claims"][0]["source_reviews"][0]["evidence"][0]["excerpt_id"] = request["sources"][1]["passages"][0]["excerpt_id"]

        def sentence_id(value, request):
            evidence = value["claims"][0]["source_reviews"][0]["evidence"][0]
            evidence["sentence_id"] = evidence.pop("excerpt_id")

        for mutate in (duplicate, wrong_owner, sentence_id):
            with self.subTest(mutation=mutate.__name__):
                result, _ = await self.run_http(mutate=mutate)
                self.assertEqual(result["status"], "invalid_response")
                self.assertFalse(result["coverage"]["complete_source_review"])
                self.assertEqual(result["claims"][0]["evidence"], [])

    async def test_transport_truncation_discards_primary_and_uses_complete_alternate(self):
        result, _ = await self.run_http(finish_reason="length")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider_coverage"]["openrouter"]["status"], "invalid_response")
        self.assertTrue(result["provider_coverage"]["gemini"]["complete_source_review"])
        self.assertEqual(result["state"], "corroborated")


if __name__ == "__main__":
    unittest.main()
