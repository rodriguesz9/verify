"""Local admission controls; all provider responses are simulated, never billed."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from helpers import valid_png, valid_wav
from app.services.hive_service import HiveV3Budget, HIVE_V3_MODEL, check_hive_media
from app.core.huggingface_client import check_ai_image_hf


def response(media_type="image"):
    return httpx.Response(200, json={"model": HIVE_V3_MODEL, "output": [{"classes": [
        {"class": "ai_generated_audio" if media_type == "audio" else "ai_generated", "value": .9}]}]})


class HiveLocalBudgetTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "0", "HIVE_V3_AUDIO_SECONDS_LIMIT": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.budget = HiveV3Budget()

    def test_missing_limits_disable_both_modalities(self):
        os.environ.pop("HIVE_V3_IMAGE_REQUEST_LIMIT", None)
        os.environ.pop("HIVE_V3_AUDIO_SECONDS_LIMIT", None)
        self.assertEqual(self.budget.reserve("image")["status"], "disabled")
        self.assertEqual(self.budget.reserve("audio", 1)["status"], "disabled")

    def test_invalid_limits_are_fail_closed(self):
        for value in ("", "-1", "+1", "0.1", "nan", "Infinity", "１００", "100001", "1000000"):
            with self.subTest(value=value), patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": value}):
                self.assertEqual(self.budget.reserve("image")["status"], "invalid_configuration")

    def test_image_exact_limit_then_no_new_admission(self):
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "2"}):
            self.assertIsNone(self.budget.reserve("image"))
            self.assertIsNone(self.budget.reserve("image"))
            self.assertEqual(self.budget.reserve("image")["status"], "budget_exhausted")

    def test_audio_requires_validated_numeric_bounded_duration(self):
        with patch.dict(os.environ, {"HIVE_V3_AUDIO_SECONDS_LIMIT": "120"}):
            for value in (None, True, False, "10", 0, -1, 121, float("nan"), float("inf")):
                with self.subTest(value=value):
                    self.assertEqual(self.budget.reserve("audio", value)["status"], "invalid_configuration")
            self.assertIsNone(self.budget.reserve("audio", 120))

    def test_audio_fractional_seconds_round_up_before_reservation(self):
        with patch.dict(os.environ, {"HIVE_V3_AUDIO_SECONDS_LIMIT": "3"}):
            self.assertIsNone(self.budget.reserve("audio", 1.01))
            self.assertIsNone(self.budget.reserve("audio", .01))
            self.assertEqual(self.budget.reserve("audio", .01)["status"], "budget_exhausted")

    def test_excess_audio_rejection_does_not_consume_smaller_capacity(self):
        with patch.dict(os.environ, {"HIVE_V3_AUDIO_SECONDS_LIMIT": "10"}):
            self.assertEqual(self.budget.reserve("audio", 11)["status"], "budget_exhausted")
            self.assertIsNone(self.budget.reserve("audio", 10))

    def test_modalities_have_separate_counters(self):
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "1", "HIVE_V3_AUDIO_SECONDS_LIMIT": "1"}):
            self.assertIsNone(self.budget.reserve("image"))
            self.assertEqual(self.budget.reserve("image")["status"], "budget_exhausted")
            self.assertIsNone(self.budget.reserve("audio", 1))

    def test_disabled_invalid_and_changed_settings_do_not_reset_usage(self):
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "1"}):
            self.assertIsNone(self.budget.reserve("image"))
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "0"}):
            self.assertEqual(self.budget.reserve("image")["status"], "disabled")
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "1"}):
            self.assertEqual(self.budget.reserve("image")["status"], "budget_exhausted")

    def test_parallel_reservations_do_not_overrun_image_limit(self):
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "7"}), ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _index: self.budget.reserve("image"), range(40)))
        self.assertEqual(sum(item is None for item in results), 7)
        self.assertTrue(all(item is None or item["status"] == "budget_exhausted" for item in results))

    def test_parallel_reservations_do_not_overrun_audio_seconds(self):
        with patch.dict(os.environ, {"HIVE_V3_AUDIO_SECONDS_LIMIT": "10"}), ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _index: self.budget.reserve("audio", 1.1), range(40)))
        self.assertEqual(sum(item is None for item in results), 5)

    def test_unknown_media_does_not_reserve(self):
        self.assertEqual(self.budget.reserve("video")["status"], "unsupported")


class HiveBudgetTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-private-key-marker",
            "HIVE_API_KEY": "", "HIVE_V3_MEDIA_TYPES": "image,audio", "HIVE_V3_IMAGE_REQUEST_LIMIT": "1",
            "HIVE_V3_AUDIO_SECONDS_LIMIT": "10"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.budget = patch("app.services.hive_service.hive_v3_budget", HiveV3Budget())
        self.budget.start()
        self.addCleanup(self.budget.stop)

    async def test_zero_limit_never_calls_http_with_present_key(self):
        with patch.dict(os.environ, {"HIVE_V3_IMAGE_REQUEST_LIMIT": "0"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            result = await check_hive_media(valid_png())
        self.assertEqual(result["status"], "disabled")
        post.assert_not_awaited()

    async def test_image_limit_reserved_before_provider_call(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response())) as post:
            self.assertTrue((await check_hive_media(valid_png()))["available"])
            result = await check_hive_media(valid_png())
        self.assertEqual(post.await_count, 1)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertNotIn("test-private-key-marker", str(result))

    async def test_audio_missing_duration_never_calls_http(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            result = await check_hive_media(valid_wav(), "evidence.wav", "audio", "audio/wav")
        self.assertEqual(result["status"], "invalid_configuration")
        post.assert_not_awaited()

    async def test_audio_budget_uses_validated_duration_not_mime_or_filename(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response("audio"))) as post:
            self.assertTrue((await check_hive_media(valid_wav(), "evidence.wav", "audio", "audio/wav", duration_seconds=9.01))["available"])
            result = await check_hive_media(valid_wav(), "other.wav", "audio", "audio/wav", duration_seconds=.01)
        self.assertEqual(post.await_count, 1)
        self.assertEqual(result["status"], "budget_exhausted")

    async def test_error_or_pending_reservation_is_not_refunded(self):
        for status in (202, 401, 402, 429, 500):
            with self.subTest(status=status), patch("app.services.hive_service.hive_v3_budget", HiveV3Budget()), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(status))) as post:
                self.assertFalse((await check_hive_media(valid_png()))["available"])
                self.assertEqual((await check_hive_media(valid_png()))["status"], "budget_exhausted")
                self.assertEqual(post.await_count, 1)

    async def test_timeout_reservation_is_not_refunded(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.TimeoutException("private-marker"))) as post:
            first = await check_hive_media(valid_png())
            second = await check_hive_media(valid_png())
        self.assertFalse(first["available"])
        self.assertNotIn("private-marker", str(first))
        self.assertEqual(second["status"], "budget_exhausted")
        self.assertEqual(post.await_count, 1)

    async def test_request_cancellation_does_not_refund_or_resend(self):
        entered = asyncio.Event()

        async def hold(*_args, **_kwargs):
            entered.set()
            await asyncio.Event().wait()

        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=hold)) as post:
            task = asyncio.create_task(check_hive_media(valid_png()))
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual((await check_hive_media(valid_png()))["status"], "budget_exhausted")
            self.assertEqual(post.await_count, 1)

    async def test_missing_key_or_media_opt_in_does_not_consume_quota(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response())) as post:
            with patch.dict(os.environ, {"HIVE_V3_API_KEY": "", "HIVE_API_KEY": ""}):
                self.assertEqual((await check_hive_media(valid_png()))["status"], "not_configured")
            with patch.dict(os.environ, {"HIVE_V3_MEDIA_TYPES": ""}):
                self.assertEqual((await check_hive_media(valid_png()))["status"], "not_configured")
            self.assertTrue((await check_hive_media(valid_png()))["available"])
            self.assertEqual(post.await_count, 1)

    async def test_legacy_v2_not_gated_by_v3_limits_or_new_duration(self):
        payload = {"status": [{"status": {"code": "0"}, "response": {"output": [
            {"classes": [{"class": "ai_generated", "score": .1}]}]}}]}
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v2", "HIVE_AUDIO_API_KEY": "test-project",
                 "HIVE_V3_IMAGE_REQUEST_LIMIT": "0", "HIVE_V3_AUDIO_SECONDS_LIMIT": "0"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=payload))) as post:
            self.assertTrue((await check_hive_media(valid_wav(), "evidence.wav", "audio", "audio/wav"))["available"])
            self.assertEqual(post.await_count, 1)
            self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "token test-project")


class HuggingFaceOptOutTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_opt_out_preserves_token_but_never_sends_data(self):
        with patch.dict(os.environ, {}, clear=True), patch("app.core.huggingface_client.HUGGINGFACE_API_TOKEN", "private-token"), \
             patch("app.core.huggingface_client.API_URL", "https://router.huggingface.co/control"), \
             patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            result = await check_ai_image_hf(valid_png())
        self.assertEqual(result["status"], "disabled")
        self.assertNotIn("private-token", str(result))
        post.assert_not_awaited()

    async def test_only_explicit_true_enables_hf(self):
        for value in ("false", "0", "1", "yes", ""):
            with self.subTest(value=value), patch.dict(os.environ, {"HUGGINGFACE_ENABLED": value}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
                self.assertEqual((await check_ai_image_hf(valid_png()))["status"], "disabled")
                post.assert_not_awaited()

    async def test_enabled_hf_still_requires_credentials(self):
        with patch.dict(os.environ, {"HUGGINGFACE_ENABLED": " TRUE "}), \
             patch("app.core.huggingface_client.HUGGINGFACE_API_TOKEN", ""), \
             patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertEqual((await check_ai_image_hf(valid_png()))["status"], "not_configured")
            post.assert_not_awaited()
