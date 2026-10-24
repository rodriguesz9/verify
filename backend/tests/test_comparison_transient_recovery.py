"""Offline 503 recovery, exact deadlines/quotas and unchanged evidence checks."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import test_source_review_generation_contract as controls
from app.core import gemini_client, openrouter_service
from app.services import source_corroboration as sources
from app.services.provider_diagnostics import http_failure_metadata


class ScopedComparisonRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_http503_then_complete_review_uses_same_request_and_two_reservations(self):
        sent = []
        client_type = httpx.AsyncClient

        def respond(request):
            payload = json.loads(request.content)
            sent.append((request.url.path, payload))
            if len(sent) == 1:
                return httpx.Response(503, json={"error": {"message": "private-provider-data"}})
            original = json.loads(payload["contents"][0]["parts"][0]["text"])
            return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
                "content": {"parts": [{"text": json.dumps(controls.answer(original))}]}}]})

        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(respond), **kwargs)

        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true",
                "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini", "GEMINI_API_KEY": "offline-fake",
                "GEMINI_MODEL_NAME": "offline-control", "GEMINI_FALLBACK_MODELS": "",
                "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true", "OPENROUTER_API_KEY": ""}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(gemini_client, "_reserve_request", new=AsyncMock()) as reserve, \
             patch.object(openrouter_service, "generate", new=AsyncMock()) as alternate, \
             patch.object(sources.random, "uniform", return_value=1), \
             patch.object(sources.asyncio, "sleep", new=AsyncMock()) as sleep, \
             patch("httpx.AsyncClient", side_effect=client):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0], sent[1])
        self.assertEqual(reserve.await_count, 2)
        alternate.assert_not_awaited()
        sleep.assert_awaited_once_with(1)
        coverage = result["provider_coverage"]["gemini"]
        self.assertEqual(coverage["transient_retry_count"], 1)
        self.assertEqual(coverage["prior_http_status"], 503)
        self.assertTrue(coverage["complete_source_review"])
        self.assertNotIn("private-provider-data", str(result))

    async def test_repeated503_stops_after_one_recovery_with_http_diagnostics(self):
        coverage = {}
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true"}), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(
                 side_effect=gemini_client.GeminiError("private", "unavailable", 503))) as generate, \
             patch.object(sources.random, "uniform", return_value=1), \
             patch.object(sources.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaises(gemini_client.GeminiError) as raised:
                await sources._gemini_comparison("unchanged", {}, coverage, 20)
        self.assertEqual(generate.await_count, 2)
        self.assertEqual(http_failure_metadata(raised.exception),
                         {"http_status": 503, "transport_failure": "provider_unavailable"})

    async def test_quota_auth_timeout_and_invalid_output_never_get_a_retry(self):
        for status, http_status in (("rate_limited", 429), ("error", 401), ("error", 402),
                                    ("error", 404), ("timeout", None), ("invalid_response", None)):
            with self.subTest(status=status, http_status=http_status), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(
                     side_effect=gemini_client.GeminiError("private", status, http_status))) as generate, \
                 patch.object(sources.asyncio, "sleep", new=AsyncMock()) as sleep:
                with self.assertRaises(gemini_client.GeminiError):
                    await sources._gemini_comparison("original", {}, {}, 20)
                generate.assert_awaited_once()
                sleep.assert_not_awaited()

    async def test_short_deadline_opt_out_and_explicit_model_fallback_do_not_expand_attempts(self):
        for deadline, config in ((2, {}), (20, {"SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "false"}),
                                  (20, {"GEMINI_FALLBACK_MODELS": "explicit-fallback"})):
            with self.subTest(deadline=deadline, config=config), \
                 patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                     "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true", **config}), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(
                     side_effect=gemini_client.GeminiError("private", "unavailable", 503))) as generate, \
                 patch.object(sources.asyncio, "sleep", new=AsyncMock()) as sleep:
                with self.assertRaises(gemini_client.GeminiError):
                    await sources._gemini_comparison("original", {}, {}, deadline)
                generate.assert_awaited_once()
                sleep.assert_not_awaited()

    async def test_second_reservation_rejection_is_not_refunded_or_repeated(self):
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true"}), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=[
                 gemini_client.GeminiError("private", "unavailable", 503),
                 gemini_client.GeminiError("local limit", "rate_limited")])) as generate, \
             patch.object(sources.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaises(gemini_client.GeminiError) as raised:
                await sources._gemini_comparison("original", {}, {}, 20)
        self.assertEqual(raised.exception.status, "rate_limited")
        self.assertEqual(generate.await_count, 2)

    async def test_cancellation_during_backoff_sends_no_second_request(self):
        coverage = {}
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true"}), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(
                 side_effect=gemini_client.GeminiError("private", "unavailable", 503))) as generate, \
             patch.object(sources.asyncio, "sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await sources._gemini_comparison("original", {}, coverage, 20)
        generate.assert_awaited_once()
        self.assertNotIn("transient_retry_count", coverage)

    async def test_retry_uses_remaining_time_not_a_new_full_deadline(self):
        values = [100, 100, 101, 102]
        loop = type("Clock", (), {"time": lambda self: values.pop(0)})()
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true"}), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=[
                 gemini_client.GeminiError("private", "unavailable", 503), "complete"])) as generate, \
             patch.object(sources.asyncio, "get_running_loop", return_value=loop), \
             patch.object(sources.random, "uniform", return_value=1), \
             patch.object(sources.asyncio, "sleep", new=AsyncMock()):
            self.assertEqual(await sources._gemini_comparison("original", {}, {}, 20), "complete")
        self.assertEqual([call.kwargs["timeout_seconds"] for call in generate.await_args_list], [20, 18])


class ProviderDiagnosticTests(unittest.TestCase):
    def test_only_bounded_numeric_http_metadata_is_exposed(self):
        for code in ("503?private", True, None, 200, 999):
            error = type("PrivateError", (), {"http_status": code})()
            self.assertEqual(http_failure_metadata(error), {})
        self.assertEqual(http_failure_metadata(openrouter_service.OpenRouterError(
            "error", "private-body", 404)), {"http_status": 404, "transport_failure": "route_not_found"})

    def test_transient_retry_after_header_is_internal_and_cannot_force_an_early_retry(self):
        self.assertIsNone(gemini_client._transient_retry_after(httpx.Response(503)))
        self.assertEqual(gemini_client._transient_retry_after(httpx.Response(
            503, headers={"retry-after": "2"})), 2)
        self.assertGreater(gemini_client._transient_retry_after(httpx.Response(
            503, headers={"retry-after": "999999999"})), 5)
        for header in ("private-invalid", "-1", "NaN", "infinity"):
            self.assertEqual(gemini_client._transient_retry_after(httpx.Response(
                503, headers={"retry-after": header})), float("inf"))
        self.assertGreater(gemini_client._transient_retry_after(httpx.Response(
            503, headers={"retry-after": "Sat, 01 Jan 2050 00:00:00 GMT"})), 5)


class RetryAfterComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_delay_is_respected_or_retry_is_abandoned(self):
        for delay, should_retry in ((2, True), (120, False), (float("inf"), False), (-1, False)):
            error = gemini_client.GeminiError("private", "unavailable", 503, delay)
            with self.subTest(delay=delay), patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "",
                    "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "true"}), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=[error, "ok"])) as generate, \
                 patch.object(sources.random, "uniform", return_value=1), \
                 patch.object(sources.asyncio, "sleep", new=AsyncMock()) as sleep:
                if should_retry:
                    self.assertEqual(await sources._gemini_comparison("original", {}, {}, 20), "ok")
                    sleep.assert_awaited_once_with(2)
                    self.assertEqual(generate.await_count, 2)
                else:
                    with self.assertRaises(gemini_client.GeminiError):
                        await sources._gemini_comparison("original", {}, {}, 20)
                    sleep.assert_not_awaited()
                    generate.assert_awaited_once()


class ProviderHttpCoverageTests(unittest.IsolatedAsyncioTestCase):
    async def test_comparison_preserves503_and404_without_body_or_extra_router_request(self):
        client_type = httpx.AsyncClient
        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(lambda _request: httpx.Response(
                404, json={"error": {"message": "private-provider-response"}})), **kwargs)
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true",
                "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini", "GEMINI_API_KEY": "offline",
                "GEMINI_FALLBACK_MODELS": "", "SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED": "false",
                "OPENROUTER_API_KEY": "offline", "OPENROUTER_ENABLED": "true",
                "OPENROUTER_MODEL": "openrouter/free", "OPENROUTER_FALLBACK_MODELS": ""}), \
             patch.object(sources, "typed_review_matrix", return_value=None), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(
                 side_effect=gemini_client.GeminiError("private-gemini", "unavailable", 503))) as gemini, \
             patch.object(openrouter_service, "_reserve_request") as reserve, \
             patch("httpx.AsyncClient", side_effect=client):
            result = await sources.corroborate_sources(controls.CLAIM, controls.documents())
        self.assertEqual(result["state"], "insufficient")
        self.assertEqual(result["provider_coverage"]["gemini"]["http_status"], 503)
        self.assertEqual(result["provider_coverage"]["openrouter"]["http_status"], 404)
        self.assertEqual(result["provider_coverage"]["openrouter"]["transport_failure"], "route_not_found")
        self.assertNotIn("private-provider-response", str(result))
        self.assertNotIn("private-gemini", str(result))
        reserve.assert_called_once()
        gemini.assert_awaited_once()

    async def test_research_exposes_only_sanitized_status_codes(self):
        from app.services import source_research
        with patch.dict(os.environ, {"SERPERAPI_KEY": "offline", "GEMINI_API_KEY": "offline",
                "OPENROUTER_API_KEY": "offline", "OPENROUTER_ENABLED": "true",
                "SOURCE_RESEARCH_ENABLED": "true"}, clear=True), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(
                 side_effect=gemini_client.GeminiError("private-gemini", "unavailable", 503))), \
             patch.object(openrouter_service, "generate", new=AsyncMock(
                 side_effect=openrouter_service.OpenRouterError("error", "private-router", 404))):
            result = await source_research.plan_source_research(controls.CLAIM, [], [], {})
        coverage = result["coverage"]["provider_coverage"]
        self.assertEqual(coverage["gemini"]["http_status"], 503)
        self.assertEqual(coverage["openrouter"]["http_status"], 404)
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["leads"], [])
        self.assertNotIn("private-", str(result))
