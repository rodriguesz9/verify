"""Offline model admission/payload controls; no credentials, billing or waits."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from app.core import gemini_client as gemini


def reply(text='{"ok":true}'):
    return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
        "content": {"parts": [{"text": text}]}}]})


class GeminiAdmissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = 100.0
        self.guard = gemini.GeminiAdmission(clock=lambda: self.now)
        self.enterContext(patch.object(gemini, "_gemini_admission", self.guard))
        self.enterContext(patch.dict(os.environ, {
            "GEMINI_API_KEY": "offline-unit-placeholder", "GEMINI_MODEL_NAME": "gemini-3.8-flash",
            "GEMINI_FALLBACK_MODELS": "", "GEMINI_LOCAL_ADMISSION_ENABLED": "true",
            "GEMINI_LOCAL_REQUESTS_PER_MINUTE": "5", "GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "60",
        }))

    def test_bounded_configurations_reject_non_ascii_and_unbounded_values(self):
        for raw, expected in [("1", 1), ("15", 15), (" 7 ", 7), ("0", 5),
                              ("16", 5), ("5.0", 5), ("NaN", 5), ("５", 5),
                              ("-1", 5), ("private-config-never-echoed", 5)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {"GEMINI_LOCAL_REQUESTS_PER_MINUTE": raw}):
                self.assertEqual(gemini._bounded_integer("GEMINI_LOCAL_REQUESTS_PER_MINUTE", 5, 1, 15), expected)
        for raw, expected in [("1", 1), ("3600", 3600), ("0", 60), ("3601", 60), ("999999", 60)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {"GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": raw}):
                self.assertEqual(gemini._bounded_integer("GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", 60, 1, 3600), expected)

    def test_only_explicit_false_disables_admission(self):
        for raw, expected in [("true", True), ("false", False), (" FALSE ", False),
                              ("", True), ("0", True), ("invalid-private-value", True)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {"GEMINI_LOCAL_ADMISSION_ENABLED": raw}):
                self.assertEqual(gemini._admission_enabled(), expected)

    async def test_concurrent_requests_share_model_window_and_never_send_above_limit(self):
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=reply())) as post:
            results = await asyncio.gather(*(gemini.generate_text(f"fixed control {n}") for n in range(12)), return_exceptions=True)
        self.assertEqual(post.await_count, 5)
        self.assertEqual(sum(isinstance(result, gemini.GeneratedText) for result in results), 5)
        failures = [result for result in results if isinstance(result, gemini.GeminiError)]
        self.assertEqual(len(failures), 7)
        self.assertTrue(all(result.status == "rate_limited" and result.http_status is None for result in failures))
        self.assertEqual(set(self.guard._models), {"gemini-3.8-flash"})
        self.assertNotIn("fixed control", repr(self.guard._models))
        self.assertNotIn("offline-unit-placeholder", repr(self.guard._models))

    async def test_failed_and_cancelled_attempts_still_consume_local_budget(self):
        with patch.dict(os.environ, {"GEMINI_LOCAL_REQUESTS_PER_MINUTE": "1"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=httpx.ReadTimeout("private-error"))) as post:
            with self.assertRaises(gemini.GeminiError) as first:
                await gemini.generate_text("fixed control")
            with self.assertRaises(gemini.GeminiError) as second:
                await gemini.generate_text("fixed control")
        self.assertEqual(first.exception.status, "timeout")
        self.assertEqual(second.exception.status, "rate_limited")
        self.assertEqual(post.await_count, 1)

        self.now += 60
        with patch.dict(os.environ, {"GEMINI_LOCAL_REQUESTS_PER_MINUTE": "1"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=asyncio.CancelledError)) as post:
            with self.assertRaises(asyncio.CancelledError):
                await gemini.generate_text("fixed control")
            with self.assertRaises(gemini.GeminiError) as cancelled_next:
                await gemini.generate_text("fixed control")
        self.assertEqual(cancelled_next.exception.status, "rate_limited")
        self.assertEqual(post.await_count, 1)

    async def test_local_window_expires_at_sixty_seconds(self):
        with patch.dict(os.environ, {"GEMINI_LOCAL_REQUESTS_PER_MINUTE": "1"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=reply())) as post:
            await gemini.generate_text("fixed control")
            self.now += 59.999
            with self.assertRaises(gemini.GeminiError):
                await gemini.generate_text("fixed control")
            self.now += .001
            await gemini.generate_text("fixed control")
        self.assertEqual(post.await_count, 2)

    async def test_model_windows_separate_but_quota_does_not_trigger_fallback(self):
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "fallback-model"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=httpx.Response(429,
                    json={"error": {"message": "private-provider-error"}}))) as post:
            with self.assertRaises(gemini.GeminiError) as raised:
                await gemini.generate_text("fixed control")
            self.assertEqual(raised.exception.status, "rate_limited")
            self.assertEqual(raised.exception.http_status, 429)
            self.assertNotIn("private-provider-error", str(raised.exception))
            with self.assertRaises(gemini.GeminiError):
                await gemini.generate_text("fixed control")
        self.assertEqual(post.await_count, 1)
        self.assertEqual(set(self.guard._models), {"gemini-3.8-flash"})
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=reply())) as post:
            value = await gemini.generate_text("fixed control", model_name="explicit-other-model")
        self.assertEqual(value.model_name, "explicit-other-model")
        self.assertEqual(post.await_count, 1)

    async def test_explicit_fallback_reserves_own_window_after_unavailability(self):
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "fallback-model"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=[httpx.Response(503), reply()])) as post:
            value = await gemini.generate_text("fixed control")
        self.assertEqual(value.model_name, "fallback-model")
        self.assertEqual(post.await_count, 2)
        self.assertEqual(len(self.guard._models["gemini-3.8-flash"][0]), 1)
        self.assertEqual(len(self.guard._models["fallback-model"][0]), 1)

    async def test_numeric_retry_after_and_retry_info_pause_without_sleep(self):
        quota = httpx.Response(429, headers={"retry-after": "90"}, json={"error": {"details": [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "120.5s"}]}})
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=[quota, reply()])) as post:
            with self.assertRaises(gemini.GeminiError):
                await gemini.generate_text("fixed control")
            self.now += 120.499
            with self.assertRaises(gemini.GeminiError):
                await gemini.generate_text("fixed control")
            self.now += .001
            await gemini.generate_text("fixed control")
        self.assertEqual(post.await_count, 2)

    def test_cooldown_durations_are_bounded_and_never_decrease_an_active_pause(self):
        gemini._reserve_request("fixed-model")
        gemini._pause_after_rate_limit("fixed-model", httpx.Response(429,
            headers={"retry-after": "999999999"}, json={"error": {"details": []}}))
        self.assertEqual(self.guard._models["fixed-model"][1], self.now + 3600)
        self.now += 5
        gemini._pause_after_rate_limit("fixed-model", httpx.Response(429, headers={"retry-after": "1"}))
        self.assertEqual(self.guard._models["fixed-model"][1], 3700)

    def test_malformed_retry_hints_use_default_cooldown_without_exposing_body(self):
        for body in ([], {"error": None}, {"error": {"details": "private-value"}},
                     {"error": {"details": [None, {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "NaNs"}]}}):
            with self.subTest(body=body):
                guard = gemini.GeminiAdmission(clock=lambda: self.now)
                with patch.object(gemini, "_gemini_admission", guard):
                    gemini._reserve_request("fixed-model")
                    gemini._pause_after_rate_limit("fixed-model", httpx.Response(429,
                        headers={"retry-after": "private-invalid-header"}, json=body))
                self.assertEqual(guard._models["fixed-model"][1], self.now + 60)
                self.assertNotIn("private", repr(guard._models))

    def test_guard_capacity_is_bounded_and_idle_records_reclaimed(self):
        guard = gemini.GeminiAdmission(clock=lambda: self.now, capacity=2)
        guard.reserve("one", 5)
        guard.reserve("two", 5)
        with self.assertRaises(gemini.GeminiError) as raised:
            guard.reserve("three", 5)
        self.assertEqual(raised.exception.status, "rate_limited")
        self.assertEqual(len(guard._models), 2)
        self.now += 60
        guard.reserve("three", 5)
        self.assertEqual(set(guard._models), {"three"})

    async def test_explicit_test_opt_out_creates_no_state_even_after_429(self):
        with patch.dict(os.environ, {"GEMINI_LOCAL_ADMISSION_ENABLED": "false"}), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=httpx.Response(429))) as post:
            for _ in range(7):
                with self.assertRaises(gemini.GeminiError):
                    await gemini.generate_text("fixed control")
        self.assertEqual(post.await_count, 7)
        self.assertEqual(self.guard._models, {})

    async def test_missing_key_and_invalid_model_create_no_state_or_http_request(self):
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock()) as post:
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), self.assertRaises(gemini.GeminiError):
                await gemini.generate_text("fixed control")
            with self.assertRaises(gemini.GeminiError) as invalid:
                await gemini.generate_text("fixed control", model_name="private/path?key=secret")
        self.assertEqual(invalid.exception.status, "invalid_configuration")
        self.assertEqual(post.await_count, 0)
        self.assertEqual(self.guard._models, {})

    async def test_oversized_multimodal_body_is_rejected_before_http_and_reservation(self):
        with patch.object(gemini, "MAX_GEMINI_REQUEST_BYTES", 1024), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock()) as post:
            with self.assertRaises(gemini.GeminiError) as raised:
                await gemini.generate_text(["fixed control", {"inline_data": {"mime_type": "image/png", "data": b"x" * 900}}])
        self.assertEqual(raised.exception.status, "input_too_large")
        self.assertEqual(post.await_count, 0)
        self.assertEqual(self.guard._models, {})

    def test_payload_budget_counts_serialized_utf8_not_character_length(self):
        body = {"text": "á" * 30}
        serialized = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with patch.object(gemini, "MAX_GEMINI_REQUEST_BYTES", len(serialized)):
            gemini._validate_request_size(body)
            with self.assertRaises(gemini.GeminiError) as raised:
                gemini._validate_request_size({"text": "á" * 31})
        self.assertEqual(raised.exception.status, "input_too_large")
        self.assertLess(gemini.MAX_GEMINI_REQUEST_BYTES, 20_000_000)

    async def test_valid_small_image_bytes_are_preserved_and_invalid_json_config_never_sent(self):
        import base64
        source = helpers.valid_png()
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=reply())) as post:
            await gemini.generate_text(["fixed control", {"inline_data": {"mime_type": "image/png", "data": source}}])
            part = post.call_args.kwargs["json"]["contents"][0]["parts"][1]["inlineData"]
            self.assertEqual(base64.b64decode(part["data"]), source)
            with self.assertRaises(gemini.GeminiError) as invalid:
                await gemini.generate_text("fixed control", temperature=float("nan"))
        self.assertEqual(invalid.exception.status, "invalid_configuration")
        self.assertEqual(post.await_count, 1)


if __name__ == "__main__":
    unittest.main()
