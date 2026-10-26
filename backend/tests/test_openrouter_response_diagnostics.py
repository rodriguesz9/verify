"""Offline response failures: no raw bodies, extra calls or partial evidence."""
import copy
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core import openrouter_service as router
from app.services import source_corroboration as sources, source_research
from app.services.provider_diagnostics import provider_failure_metadata
import test_source_review_generation_contract as controls


def envelope():
    return {"model": "vendor/control:free", "choices": [{"finish_reason": "stop",
            "message": {"content": "{}"}}], "usage": {"cost": 0}}


class ResponseValidationTests(unittest.TestCase):
    def rejected(self, data, issue):
        with self.assertRaises(router.OpenRouterError) as raised:
            router._complete_response(data, "openrouter/free")
        self.assertEqual(raised.exception.status, "invalid_response")
        self.assertEqual(provider_failure_metadata(raised.exception), {"response_issue": issue})
        self.assertNotIn("private-control", str(raised.exception))

    def test_complete_response_preserves_content_and_zero_cost(self):
        result = router._complete_response(envelope(), "openrouter/free")
        self.assertEqual(result, "{}")
        self.assertEqual(result.model_name, "vendor/control:free")

    def test_token_limit_identified_before_content_even_when_reasoning_is_present(self):
        for value in (None, "", "{private-control", "{}"):
            data = envelope()
            data["choices"][0].update(finish_reason="length", message={"content": value,
                "reasoning": "private-control", "reasoning_details": [{"text": "private-control"}]})
            self.rejected(data, "token_limit")

    def test_abnormal_finish_never_accepts_valid_looking_content(self):
        for reason in (None, "tool_calls", "error", "private-control"):
            data = envelope()
            data["choices"][0]["finish_reason"] = reason
            self.rejected(data, "unexpected_finish")

    def test_explicit_content_filter_is_identified_as_a_protection_block(self):
        data = envelope()
        data["choices"][0]["finish_reason"] = "content_filter"
        self.rejected(data, "content_blocked")

    def test_empty_visible_content_does_not_fall_back_to_reasoning(self):
        for value in (None, "", " \n\t"):
            data = envelope()
            data["choices"][0]["message"].update(content=value, reasoning="private-control")
            self.rejected(data, "empty_content")

    def test_non_string_or_oversized_content_is_not_usable(self):
        for value in (False, 7, {}, ["private-control"]):
            data = envelope()
            data["choices"][0]["message"]["content"] = value
            self.rejected(data, "invalid_content")
        data = envelope()
        data["choices"][0]["message"]["content"] = "x" * 30001
        self.rejected(data, "content_limit")

    def test_malformed_envelopes_have_fixed_diagnostic(self):
        for data in (None, [], {}, {"choices": []}, {"choices": [None]},
                     {"choices": [{"finish_reason": "stop"}]},
                     {"choices": [{"finish_reason": "stop", "message": {}}]},
                     {**envelope(), "usage": None}):
            self.rejected(data, "malformed_envelope")

    def test_nonzero_and_invalid_costs_remain_rejected(self):
        for cost in (.00001, -1, True, "0", float("inf"), float("nan")):
            data = envelope()
            data["usage"]["cost"] = cost
            self.rejected(data, "unexpected_cost")

    def test_http200_error_overrides_even_complete_looking_choices(self):
        for code in (401, 402, 429, 503, 599):
            data = envelope()
            data["error"] = {"code": code, "message": "private-control",
                             "metadata": {"credential": "private-control"}}
            with self.assertRaises(router.OpenRouterError) as raised:
                router._complete_response(data, "openrouter/free")
            metadata = provider_failure_metadata(raised.exception)
            self.assertEqual(raised.exception.status, "rate_limited" if code in {402, 429} else "error")
            self.assertEqual(metadata["response_issue"], "provider_error")
            self.assertNotIn("http_status", metadata)
            self.assertNotIn("private-control", json.dumps(metadata) + str(raised.exception))
            if code != 599:
                self.assertEqual(metadata["provider_error_code"], code)
            else:
                self.assertEqual(metadata, {"response_issue": "provider_error"})

    def test_invalid_error_codes_are_not_exported_or_mistaken_for_quota(self):
        for code in (None, True, 429.0, "429", {}, 200, 600):
            self.rejected({"error": {"code": code, "message": "private-control"}}, "malformed_envelope")

    def test_metadata_uses_only_positive_list_and_distinguishes_body_code(self):
        error = router.OpenRouterError("error", "private-control", 503,
            response_issue="private-control", provider_error_code=429)
        self.assertEqual(provider_failure_metadata(error),
            {"http_status": 503, "transport_failure": "provider_unavailable"})
        for issue in (True, [], {}, None):
            error.response_issue = issue
            self.assertNotIn("response_issue", provider_failure_metadata(error))


class ResponseTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "offline-control",
            "OPENROUTER_ENABLED": "true", "OPENROUTER_MODEL": "openrouter/free",
            "OPENROUTER_FALLBACK_MODELS": "vendor/control:free",
            "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini",
            "SOURCE_RESEARCH_ENABLED": "true", "SERPERAPI_KEY": "offline-control"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.real_client = httpx.AsyncClient
        self.sent = []

    def mocked_client(self, body):
        def respond(request):
            self.sent.append(json.loads(request.content))
            return httpx.Response(200, json=copy.deepcopy(body))
        return lambda **kwargs: self.real_client(transport=httpx.MockTransport(respond), **kwargs)

    async def test_quota_error_body_sets_cooldown_once_and_never_uses_free_alternate(self):
        for code in (402, 429):
            self.sent.clear()
            with self.subTest(code=code), patch.object(router, "_reserve_request") as reserve, \
                 patch.object(router, "_cooldown_until", 0), \
                 patch("httpx.AsyncClient", side_effect=self.mocked_client({"error": {
                     "code": code, "message": "private-control"}})):
                with self.assertRaises(router.OpenRouterError) as raised:
                    await router.generate("control")
                self.assertGreater(router._cooldown_until, 0)
            self.assertEqual(raised.exception.status, "rate_limited")
            self.assertEqual(len(self.sent), 1)
            reserve.assert_called_once()
            self.assertTrue(all(price == 0 for price in self.sent[0]["provider"]["max_price"].values()))

    async def test_comparison_retains_token_diagnostic_and_never_votes_on_partial_json(self):
        body = envelope()
        body["choices"][0].update(finish_reason="length", message={"content": "{private-control"})
        with patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(router, "_reserve_request") as reserve, \
             patch("httpx.AsyncClient", side_effect=self.mocked_client(body)):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["state"], "insufficient")
        self.assertEqual(result["provider_coverage"]["openrouter"]["response_issue"], "token_limit")
        self.assertNotIn("private-control", str(result))
        self.assertEqual(len(self.sent), 1)
        reserve.assert_called_once()

    async def test_primary_provider_error_uses_only_existing_gemini_alternate(self):
        from app.core import gemini_client
        def completed(prompt, **_kwargs):
            return json.dumps(controls.answer(json.loads(prompt)))
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter",
                 "GEMINI_API_KEY": "offline-control"}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(router, "_reserve_request") as reserve, \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=completed)) as alternate, \
             patch("httpx.AsyncClient", side_effect=self.mocked_client({"error": {
                 "code": 503, "message": "private-control"}})):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["provider_coverage"]["openrouter"]["provider_error_code"], 503)
        self.assertTrue(result["provider_coverage"]["gemini"]["complete_source_review"])
        self.assertNotIn("private-control", str(result))
        self.assertEqual(len(self.sent), 1)
        reserve.assert_called_once()
        alternate.assert_awaited_once()
        self.assertGreater(alternate.await_args.kwargs["timeout_seconds"], 0)
        self.assertLessEqual(alternate.await_args.kwargs["timeout_seconds"], 120)

    async def test_primary_partial_output_cannot_override_valid_insufficient_alternate(self):
        from app.core import gemini_client
        def insufficient(prompt, **_kwargs):
            return json.dumps(controls.answer(json.loads(prompt), insufficient=True))
        body = envelope()
        body["choices"][0].update(finish_reason="length", message={"content": "{}"})
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter",
                 "GEMINI_API_KEY": "offline-control"}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(router, "_reserve_request"), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=insufficient)) as alternate, \
             patch("httpx.AsyncClient", side_effect=self.mocked_client(body)):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["state"], "insufficient")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["claims"][0]["evidence"], [])
        self.assertEqual(result["provider_coverage"]["openrouter"]["response_issue"], "token_limit")
        alternate.assert_awaited_once()
        self.assertEqual(len(self.sent), 1)

    async def test_research_retains_provider_error_without_query_or_raw_body(self):
        with patch.object(router, "_reserve_request"), \
             patch("httpx.AsyncClient", side_effect=self.mocked_client({"error": {
                 "code": 503, "message": "private-control", "metadata": {"raw": "private-control"}}})):
            result = await source_research.plan_source_research(controls.CLAIM, [], [], {})
        coverage = result["coverage"]["provider_coverage"]["openrouter"]
        self.assertEqual(coverage["status"], "error")
        self.assertEqual(coverage["provider_error_code"], 503)
        self.assertNotIn("http_status", coverage)
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["leads"], [])
        self.assertNotIn("private-control", str(result))
        self.assertEqual(len(self.sent), 1)

    async def test_auxiliary_extraction_preserves_only_safe_failure_kind(self):
        body = envelope()
        body["choices"][0]["message"]["content"] = None
        with patch.object(router, "_reserve_request"), \
             patch("httpx.AsyncClient", side_effect=self.mocked_client(body)):
            result = await router.analyze_with_openrouter("Controle factual inventado.")
        self.assertFalse(result["available"])
        self.assertEqual(result["response_issue"], "empty_content")
        self.assertEqual(result["claims"], [])
        self.assertEqual(len(self.sent), 1)
