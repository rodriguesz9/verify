"""A failed examination may use one alternate; a valid result never does."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core import gemini_client, openrouter_service
from app.services import source_corroboration as sources
import test_source_review_generation_contract as controls


class TechnicalFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini",
            "GEMINI_API_KEY": "offline-control", "GEMINI_MODEL_NAME": "offline-control",
            "GEMINI_FALLBACK_MODELS": "", "GEMINI_LOCAL_ADMISSION_ENABLED": "false",
            "OPENROUTER_API_KEY": "offline-control", "OPENROUTER_ENABLED": "true",
            "OPENROUTER_MODEL": "openrouter/free", "OPENROUTER_FALLBACK_MODELS": "",
        }, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.real_client = httpx.AsyncClient

    async def via_rest(self, primary, primary_fault, *, alternate_insufficient=False, both_faults=False):
        sent = []

        async def respond(request):
            payload = json.loads(request.content)
            provider = "openrouter" if request.url.host == "openrouter.ai" else "gemini"
            if provider == "openrouter":
                prompt = payload["messages"][-1]["content"]
                schema = payload["response_format"]["json_schema"]["schema"]
                self.assertEqual(payload["model"], "openrouter/free")
                self.assertTrue(all(price == 0 for price in payload["provider"]["max_price"].values()))
            else:
                prompt = payload["contents"][0]["parts"][0]["text"]
                schema = payload["generationConfig"]["responseSchema"]
            parsed = json.loads(prompt)
            sent.append({"provider": provider, "prompt": prompt, "schema": schema})
            value = controls.answer(parsed, insufficient=alternate_insufficient and provider != primary)
            fault = primary_fault if provider == primary or both_faults else None
            if fault == "matrix":
                value["claims"][0]["source_reviews"].pop()
            text = "{private-invalid-response" if fault == "json" else json.dumps(value)
            if provider == "openrouter":
                return httpx.Response(200, json={"model": "vendor/control:free", "choices": [{
                    "finish_reason": "length" if fault == "length" else "stop",
                    "message": {"content": text}}], "usage": {"cost": 0}})
            return httpx.Response(200, json={"candidates": [{
                "finishReason": "MAX_TOKENS" if fault == "length" else "STOP",
                "content": {"parts": [{"text": text}]}}]})

        def client(**kwargs):
            return self.real_client(transport=httpx.MockTransport(respond), **kwargs)

        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": primary}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(openrouter_service, "_reserve_request") as router_reserve, \
             patch.object(gemini_client, "_reserve_request", new=AsyncMock()) as gemini_reserve, \
             patch("httpx.AsyncClient", side_effect=client):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual([entry["provider"] for entry in sent],
                         [primary, "gemini" if primary == "openrouter" else "openrouter"])
        self.assertEqual(sent[0]["prompt"], sent[1]["prompt"], "Never send the failed output to the alternate.")
        gemini_schema = next(item["schema"] for item in sent if item["provider"] == "gemini")
        router_schema = next(item["schema"] for item in sent if item["provider"] == "openrouter")
        self.assertEqual(gemini_schema, sources._gemini_schema(router_schema))
        router_reserve.assert_called_once()
        gemini_reserve.assert_awaited_once()
        self.assertEqual(result["provider_coverage"][primary]["status"], "invalid_response")
        self.assertNotIn("private-invalid-response", str(result))
        return result

    async def test_gemini_truncated_response_can_use_one_complete_free_router_review(self):
        result = await self.via_rest("gemini", "length")
        self.assertEqual(result["state"], "corroborated")
        self.assertTrue(result["provider_coverage"]["openrouter"]["complete_source_review"])
        self.assertEqual({item["excerpt"] for item in result["claims"][0]["evidence"]}, set(controls.QUOTES))

    async def test_router_truncated_response_can_use_one_complete_gemini_review(self):
        result = await self.via_rest("openrouter", "length")
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["provider_coverage"]["openrouter"]["response_issue"], "token_limit")
        self.assertTrue(result["provider_coverage"]["gemini"]["complete_source_review"])

    async def test_malformed_json_can_use_complete_alternate_in_either_direction(self):
        for primary in ("gemini", "openrouter"):
            with self.subTest(primary=primary):
                result = await self.via_rest(primary, "json")
                self.assertEqual(result["state"], "corroborated")

    async def test_incomplete_matrix_discards_every_partial_vote_before_alternate(self):
        for primary in ("gemini", "openrouter"):
            with self.subTest(primary=primary):
                result = await self.via_rest(primary, "matrix", alternate_insufficient=True)
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["claims"][0]["evidence"], [])
                self.assertEqual(result["provider_coverage"][primary]["reviewed_source_pair_count"], 1)
                alternate = "gemini" if primary == "openrouter" else "openrouter"
                self.assertTrue(result["provider_coverage"][alternate]["complete_source_review"])

    async def test_two_invalid_responses_stop_with_no_combined_or_partial_evidence(self):
        for primary in ("gemini", "openrouter"):
            with self.subTest(primary=primary):
                result = await self.via_rest(primary, "matrix", both_faults=True)
                self.assertEqual(result["status"], "invalid_response")
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["claims"][0]["evidence"], [])
                self.assertFalse(result["coverage"]["complete_source_review"])

    async def test_complete_valid_insufficient_review_never_asks_another_provider(self):
        async def insufficient(prompt, **_kwargs):
            return json.dumps(controls.answer(json.loads(prompt), insufficient=True))
        for primary in ("gemini", "openrouter"):
            with self.subTest(primary=primary), \
                 patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": primary}), \
                 patch.object(sources, "typed_review_matrix", return_value=None), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=insufficient)) as gemini, \
                 patch.object(openrouter_service, "generate", new=AsyncMock(side_effect=insufficient)) as router:
                result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["provider_coverage"][primary]["status"], "success")
            self.assertEqual(result["state"], "insufficient")
            self.assertTrue(result["coverage"]["complete_source_review"])
            (gemini if primary == "gemini" else router).assert_awaited_once()
            (router if primary == "gemini" else gemini).assert_not_awaited()

    async def test_policy_blocks_and_bad_configuration_never_switch_provider(self):
        for issue, status in (("content_blocked", "invalid_response"), ("unexpected_cost", "invalid_response"),
                              (None, "invalid_configuration"), (None, "input_too_large")):
            error = gemini_client.GeminiError("private-policy-details", status)
            error.response_issue = issue
            with self.subTest(issue=issue, status=status), \
                 patch.object(sources, "typed_review_matrix", return_value=None), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=error)), \
                 patch.object(openrouter_service, "generate", new=AsyncMock()) as alternate:
                result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
            self.assertEqual(result["state"], "insufficient")
            self.assertEqual(result["status"], status)
            alternate.assert_not_awaited()
            self.assertNotIn("private-policy-details", str(result))

    async def test_absent_alternate_does_not_erase_invalid_primary_diagnostic(self):
        with patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(return_value="{invalid")), \
             patch.object(openrouter_service, "generate", new=AsyncMock(side_effect=
                 openrouter_service.OpenRouterError("not_configured", "private-key"))) as alternate:
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["status"], "invalid_response")
        self.assertEqual(result["provider_coverage"]["openrouter"]["status"], "not_configured")
        alternate.assert_awaited_once()
        self.assertNotIn("private-key", str(result))

    async def test_alternate_timeout_is_joined_within_the_original_remaining_budget(self):
        cleaned = asyncio.Event()
        async def stalled(*_args, **kwargs):
            self.assertTrue(0 < kwargs["timeout_seconds"] <= .04)
            try:
                await asyncio.Future()
            finally:
                cleaned.set()
        with patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(return_value="{invalid")) as first, \
             patch.object(openrouter_service, "generate", new=AsyncMock(side_effect=stalled)) as alternate:
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents(), timeout_seconds=.04)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["state"], "insufficient")
        self.assertTrue(cleaned.is_set())
        first.assert_awaited_once()
        alternate.assert_awaited_once()

    async def test_caller_cancellation_cleans_alternate_without_a_third_attempt(self):
        started, cleaned = asyncio.Event(), asyncio.Event()
        async def stalled(*_args, **_kwargs):
            started.set()
            try:
                await asyncio.Future()
            finally:
                cleaned.set()
        with patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(return_value="{invalid")) as first, \
             patch.object(openrouter_service, "generate", new=AsyncMock(side_effect=stalled)) as alternate:
            task = asyncio.create_task(sources.corroborate_sources(controls.CLAIM, controls.documents()))
            try:
                await asyncio.wait_for(started.wait(), timeout=1)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertTrue(cleaned.is_set())
        first.assert_awaited_once()
        alternate.assert_awaited_once()
