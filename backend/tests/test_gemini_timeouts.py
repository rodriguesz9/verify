"""Offline deadline regressions; no long waits or provider credentials."""
import asyncio
import json
import os
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from app.core.gemini_client import generate_text, gemini_timeout_seconds, GeminiError, GeneratedText
from app.core.gemini_analyzer import _extract_image_text_remote
from app.services import media_analysis

CLIENT = httpx.AsyncClient


class GeminiDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_oversized_image_is_not_forwarded_to_another_provider(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}), \
                patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(
                    side_effect=GeminiError("Envie uma imagem menor.", "input_too_large"))), \
                patch("app.core.openrouter_service.extract_image_text", new=AsyncMock()) as alternate:
            result = await _extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertEqual(result["status"], "input_too_large")
        self.assertFalse(result["available"])
        alternate.assert_not_awaited()

    def test_configuration_is_bounded_without_echoing_invalid_values(self):
        for raw, expected in [("10", 10), ("60", 60), ("90", 90), (" 75 ", 75),
                              ("9", 60), ("91", 60), ("", 60), ("-1", 60),
                              ("NaN", 60), ("inf", 60), ("60.0", 60), ("６０", 60)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {"GEMINI_REQUEST_TIMEOUT_SECONDS": raw}):
                self.assertEqual(gemini_timeout_seconds(), expected)

    async def test_valid_reply_uses_longer_transport_and_one_shared_fallback_deadline(self):
        seen = []
        deadline_calls = []
        original_timeout = asyncio.timeout
        def timeout(value):
            deadline_calls.append(value)
            return original_timeout(value)
        def handler(request):
            seen.append(request)
            if len(seen) == 1:
                return httpx.Response(503, request=request)
            return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
                "content": {"parts": [{"text": '{"text":"Nao pague R$ 123,45"}'}]}}]}, request=request)
        def client(**kwargs):
            limits = kwargs["timeout"]
            self.assertEqual(limits.read, 60)
            self.assertEqual(limits.connect, 10)
            self.assertEqual(limits.write, 15)
            self.assertEqual(limits.pool, 5)
            self.assertFalse(kwargs["trust_env"])
            self.assertFalse(kwargs["follow_redirects"])
            return CLIENT(transport=httpx.MockTransport(handler), **kwargs)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_MODEL_NAME": "primary-test",
                "GEMINI_FALLBACK_MODELS": "fallback-test", "GEMINI_REQUEST_TIMEOUT_SECONDS": "60"}), \
                patch("app.core.gemini_client.httpx.AsyncClient", side_effect=client), \
                patch("app.core.gemini_client.asyncio.timeout", side_effect=timeout):
            result = await generate_text("fixed control")
        self.assertEqual(result.model_name, "fallback-test")
        self.assertEqual(json.loads(result)["text"], "Nao pague R$ 123,45")
        self.assertEqual(len(seen), 2)
        self.assertEqual(deadline_calls, [60])

    async def test_http_503_is_explicit_unavailable_and_never_retried_implicitly(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_FALLBACK_MODELS": ""}), \
                patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(503))) as post:
            with self.assertRaises(GeminiError) as raised:
                await generate_text("fixed control")
        self.assertEqual(raised.exception.status, "unavailable")
        self.assertEqual(raised.exception.http_status, 503)
        self.assertEqual(post.await_count, 1)

    async def test_total_deadline_expiration_is_sanitized(self):
        class Expired:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *_args):
                raise TimeoutError("private-data-never-returned")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}), \
                patch("app.core.gemini_client.asyncio.timeout", return_value=Expired()), \
                patch("app.core.gemini_client._generate_text", new=AsyncMock(return_value="control")):
            with self.assertRaises(GeminiError) as raised:
                await generate_text("fixed control")
        self.assertEqual(raised.exception.status, "timeout")
        self.assertNotIn("private-data", str(raised.exception))

    async def test_outer_ocr_deadline_does_not_cancel_core_after_twelve_seconds(self):
        deadlines = []
        async def wait(coro, timeout):
            deadlines.append(timeout)
            return await coro
        reply = GeneratedText('{"text":"Nao pague R$ 123,45"}')
        reply.model_name = "control-test"
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_REQUEST_TIMEOUT_SECONDS": "60"}), \
                patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(return_value=reply)), \
                patch("app.core.gemini_analyzer.asyncio.wait_for", side_effect=wait):
            result = await _extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertTrue(result["available"])
        self.assertEqual(deadlines, [62])

    async def test_media_layers_reserve_time_for_reading_and_keep_other_detectors_bounded(self):
        observed = {}
        def job(label):
            async def run(*_args, **_kwargs):
                return {"label": label, "available": False}
            return run
        async def layer(coro, timeout):
            result = await coro
            observed[result["label"]] = timeout
            return result
        names = {"check_deepfake": "sightengine", "check_ai_image_hf": "hf", "check_hive_media": "hive",
                 "extract_metadata": "metadata", "verify_c2pa": "c2pa", "search_context_and_provenance": "context",
                 "extract_text_from_image": "ocr", "analyze_image_with_vision": "vision",
                 "analyze_audio_quick_for_demonstration": "audio", "detect_synthetic_speech": "speech"}
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"GEMINI_REQUEST_TIMEOUT_SECONDS": "90"}))
            for name, label in names.items():
                stack.enter_context(patch.object(media_analysis, name, side_effect=job(label)))
            stack.enter_context(patch.object(media_analysis, "hive_v3_enabled", return_value=True))
            stack.enter_context(patch.object(media_analysis, "safe_layer", side_effect=layer))
            await media_analysis.image_layers(b"control", "image/png", "control.png")
            await media_analysis.audio_layers(b"control", "audio/wav")
        self.assertEqual(observed["ocr"], 130)
        self.assertEqual(observed["vision"], 95)
        self.assertEqual(observed["audio"], 135)
        self.assertEqual(observed["hive"], 50)
        for name in ("sightengine", "hf", "metadata", "c2pa", "context", "speech"):
            self.assertEqual(observed[name], 18)

    async def test_fallback_timeout_does_not_hide_primary_provider_unavailability(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}), \
                patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(
                    side_effect=GeminiError("Gemini indisponível (HTTP 503).", "unavailable", 503))), \
                patch("app.core.openrouter_service.extract_image_text", new=AsyncMock(
                    side_effect=asyncio.TimeoutError("private-data-never-returned"))):
            result = await _extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["gemini_status"], "unavailable")
        self.assertEqual(result["fallback_status"], "timeout")
        self.assertNotIn("private-data", json.dumps(result))

    async def test_ocr_fallback_has_time_to_use_its_twenty_five_second_client(self):
        deadlines = []
        async def wait(coro, timeout):
            deadlines.append(timeout)
            return await coro
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_REQUEST_TIMEOUT_SECONDS": "60"}), \
                patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(
                    side_effect=GeminiError("Gemini indisponível (HTTP 503).", "unavailable", 503))), \
                patch("app.core.openrouter_service.extract_image_text", new=AsyncMock(
                    return_value={"available": True, "status": "success", "text": "Nao pague", "provider": "openrouter"})), \
                patch("app.core.gemini_analyzer.asyncio.wait_for", side_effect=wait):
            result = await _extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertTrue(result["available"])
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(deadlines, [62, 27])
