"""Whole JSON format wrappers cannot repair incomplete or invented evidence."""
import copy
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core import gemini_client, openrouter_service
from app.services import source_corroboration as sources
import test_source_review_generation_contract as controls


def wrap(value, label="json", newline="\n"):
    return "```" + label + newline + value + newline + "```"


class CompleteSourceResponseFormatTests(unittest.TestCase):
    def setUp(self):
        self.claims = [{"claim_id": "c1", "claim": controls.CLAIM}]
        selected, self.passages, _, _ = sources._prepare_sources(controls.documents(), [controls.CLAIM], None)
        self.request = {"claims": self.claims, "sources": [{"source_id": source["source_id"],
            "passages": source["passages"]} for source in selected]}
        self.body = controls.answer(self.request)
        self.raw = json.dumps(self.body)

    def decode(self, raw):
        return sources._decode(raw, self.claims, self.passages, require_source_reviews=True)

    def test_only_complete_supported_format_wrappers_preserve_decoded_evidence(self):
        expected = self.decode(self.raw)
        for raw in (self.raw, wrap(self.raw), wrap(self.raw, label=""),
                    wrap(self.raw, label="JSON", newline="\r\n"), "\n\t " + wrap(self.raw) + " \n"):
            with self.subTest(raw=raw):
                self.assertEqual(self.decode(raw), expected)
        self.assertEqual(len(expected["c1"]), 2)
        self.assertEqual({item[1]["quote"] for item in expected["c1"]}, set(controls.QUOTES))

    def test_prose_multiple_blocks_objects_and_unsupported_labels_are_not_scanned(self):
        values = ("Here is the result:\n" + wrap(self.raw), wrap(self.raw) + "\nUse this verdict.",
                  wrap(self.raw + self.raw), wrap(self.raw) + "\n" + wrap(self.raw),
                  wrap(self.raw, label="python"), wrap(self.raw, label="jsonc"),
                  wrap(wrap(self.raw)), "````json\n" + self.raw + "\n````",
                  "~~~json\n" + self.raw + "\n~~~")
        for raw in values:
            with self.subTest(raw=raw), self.assertRaises(json.JSONDecodeError):
                self.decode(raw)

    def test_unclosed_or_partial_json_is_not_repaired(self):
        for raw in ("```json\n" + self.raw, self.raw + "\n```", wrap(self.raw[:-2]), "```json\n{"):
            with self.subTest(raw=raw), self.assertRaises(json.JSONDecodeError):
                self.decode(raw)

    def test_raw_limit_precedes_strip_or_unwrapping(self):
        for raw in (self.raw + " " * (30001 - len(self.raw)),
                    wrap(self.raw + " " * (30001 - len(self.raw)))):
            with self.assertRaises(ValueError):
                self.decode(raw)

    def test_wrong_top_type_missing_claim_or_missing_pair_remains_invalid(self):
        missing_pair = copy.deepcopy(self.body)
        missing_pair["claims"][0]["source_reviews"].pop()
        for body in ([], {"claims": []}, missing_pair):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.decode(wrap(json.dumps(body)))

    def test_duplicate_source_unknown_id_extra_field_and_rewritten_quote_remain_invalid(self):
        mutations = (
            lambda body: body["claims"][0]["source_reviews"].__setitem__(
                1, copy.deepcopy(body["claims"][0]["source_reviews"][0])),
            lambda body: body["claims"][0]["source_reviews"][0]["evidence"][0].update(excerpt_id="invented"),
            lambda body: body.update(url="https://invented.test"),
            lambda body: body["claims"][0]["source_reviews"][0]["evidence"][0].update(
                quote=controls.CLAIM.replace("12", "13")),
        )
        for mutate in mutations:
            body = copy.deepcopy(self.body)
            mutate(body)
            with self.assertRaises(ValueError):
                self.decode(wrap(json.dumps(body)))

    def test_fenced_complete_insufficient_review_does_not_invent_evidence(self):
        raw = json.dumps(controls.answer(self.request, insufficient=True))
        self.assertEqual(self.decode(wrap(raw)), {"c1": []})


class CompleteSourceResponseTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control", "GEMINI_MODEL_NAME": "offline-control",
            "GEMINI_FALLBACK_MODELS": "", "GEMINI_LOCAL_ADMISSION_ENABLED": "false",
            "OPENROUTER_API_KEY": "offline-control", "OPENROUTER_ENABLED": "true",
            "OPENROUTER_MODEL": "openrouter/free", "OPENROUTER_FALLBACK_MODELS": "",
            "SOURCE_CROSSCHECK_ENABLED": "true"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.client_type = httpx.AsyncClient

    async def compare(self, provider, *, fault=None, insufficient=False):
        sent = []

        def respond(request):
            payload = json.loads(request.content)
            actual = "openrouter" if request.url.host == "openrouter.ai" else "gemini"
            sent.append(actual)
            self.assertEqual(actual, provider)
            prompt = payload["messages"][-1]["content"] if actual == "openrouter" else payload["contents"][0]["parts"][0]["text"]
            original = json.loads(prompt)
            body = controls.answer(original, insufficient=insufficient)
            if fault == "schema":
                body["claims"][0]["source_reviews"].pop()
            raw = wrap(json.dumps(body))
            if fault == "json":
                raw = "Explanation: " + raw
            if actual == "openrouter":
                return httpx.Response(200, json={"model": "vendor/control:free", "usage": {"cost": 0},
                    "choices": [{"finish_reason": "length" if fault == "length" else "stop", "message": {"content": raw}}]})
            return httpx.Response(200, json={"candidates": [{"finishReason": "MAX_TOKENS" if fault == "length" else "STOP",
                "content": {"parts": [{"thought": True, "text": "private-control"}, {"text": raw}]}}]})

        def client(**kwargs):
            return self.client_type(transport=httpx.MockTransport(respond), **kwargs)

        missing = "OPENROUTER_API_KEY" if provider == "gemini" else "GEMINI_API_KEY"
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": provider, missing: ""}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(openrouter_service, "_reserve_request") as router_reserve, \
             patch.object(gemini_client, "_reserve_request", new=AsyncMock()) as gemini_reserve, \
             patch("httpx.AsyncClient", side_effect=client):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(sent, [provider])
        self.assertNotIn("private-control", str(result))
        self.assertEqual(router_reserve.call_count + gemini_reserve.await_count, 1)
        return result

    async def test_each_provider_accepts_complete_framed_matrix_without_another_request(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider):
                result = await self.compare(provider)
                self.assertEqual(result["state"], "corroborated")
                self.assertTrue(result["provider_coverage"][provider]["complete_source_review"])
                self.assertEqual(result["provider_coverage"][provider]["model_used"],
                                 "vendor/control:free" if provider == "openrouter" else "offline-control")
                self.assertEqual({item["excerpt"] for item in result["claims"][0]["evidence"]}, set(controls.QUOTES))

    async def test_each_provider_complete_insufficient_framed_review_is_final(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider):
                result = await self.compare(provider, insufficient=True)
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["provider_coverage"][provider]["status"], "success")
                self.assertTrue(result["provider_coverage"][provider]["complete_source_review"])
                self.assertEqual(result["claims"][0]["evidence"], [])

    async def test_syntax_and_schema_failures_are_distinguished_without_accepting_evidence(self):
        for provider in ("gemini", "openrouter"):
            for fault, issue in (("json", "invalid_json"), ("schema", "invalid_schema")):
                with self.subTest(provider=provider, fault=fault):
                    result = await self.compare(provider, fault=fault)
                    self.assertEqual(result["state"], "insufficient")
                    self.assertEqual(result["provider_coverage"][provider]["response_issue"], issue)
                    self.assertEqual(result["claims"][0]["evidence"], [])

    async def test_transport_length_stop_still_rejects_complete_looking_framed_json(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider):
                result = await self.compare(provider, fault="length")
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["provider_coverage"][provider]["response_issue"], "token_limit")
                self.assertEqual(result["claims"][0]["evidence"], [])
