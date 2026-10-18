"""Bounded single Hive attempt; simulated HTTP only, never billable retries."""
import asyncio
from contextlib import ExitStack
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import helpers  # disables dotenv/provider credentials before application imports
from app.services import hive_service, media_analysis
from app.services.media_validation import ValidatedMedia


class HiveDeadlineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-only",
            "HIVE_API_KEY": "test-only", "HIVE_V3_MEDIA_TYPES": "image,audio",
            "HIVE_V3_IMAGE_REQUEST_LIMIT": "1", "HIVE_V3_AUDIO_SECONDS_LIMIT": "5"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.budget = patch.object(hive_service, "hive_v3_budget", hive_service.HiveV3Budget())
        self.budget.start()
        self.addCleanup(self.budget.stop)

    async def test_v3_total_and_transport_phases_are_explicit_without_retry_or_redirect(self):
        original_client, original_timeout = httpx.AsyncClient, asyncio.timeout
        clients, deadlines = [], []
        def client(*args, **kwargs):
            clients.append(kwargs)
            return original_client(*args, **kwargs)
        def timeout(value):
            deadlines.append(value)
            return original_timeout(value)
        response = httpx.Response(200, json={"model": hive_service.HIVE_V3_MODEL,
            "output": [{"classes": [{"class": "ai_generated", "value": .9}]}]})
        with patch.object(original_client, "post", new=AsyncMock(return_value=response)) as post, \
             patch.object(hive_service.httpx, "AsyncClient", side_effect=client), \
             patch.object(hive_service.asyncio, "timeout", side_effect=timeout):
            result = await hive_service.check_hive_media(b"image-control", "image.png", "image", "image/png")
        self.assertTrue(result["available"])
        self.assertEqual(deadlines, [45.0])
        self.assertEqual(post.await_count, 1)
        self.assertFalse(clients[0]["trust_env"])
        self.assertFalse(clients[0]["follow_redirects"])
        phases = clients[0]["timeout"]
        self.assertEqual((phases.read, phases.connect, phases.write, phases.pool), (45.0, 10.0, 30.0, 5.0))
        self.assertEqual(hive_service.HIVE_LAYER_TIMEOUT_SECONDS, 50.0)

    async def test_total_deadline_expiration_preserves_reservation_and_does_not_resend(self):
        async def pending(*_args, **_kwargs):
            await asyncio.Event().wait()
        with patch.object(hive_service, "HIVE_REQUEST_TIMEOUT_SECONDS", .01), \
             patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=pending)) as post:
            result = await asyncio.wait_for(hive_service.check_hive_media(b"image-control"), timeout=1)
            again = await hive_service.check_hive_media(b"image-control")
        self.assertEqual(result["status"], "timeout")
        self.assertFalse(result["available"])
        self.assertIn("não houve reenvio", result["reason"])
        self.assertEqual(again["status"], "budget_exhausted")
        self.assertEqual(post.await_count, 1)

    async def test_transport_timeout_preserves_single_attempt_and_hides_private_error(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ReadTimeout("private-do-not-expose"))) as post:
            result = await hive_service.check_hive_media(b"audio-control", "sample.wav", "audio", "audio/wav", duration_seconds=5)
            again = await hive_service.check_hive_media(b"audio-control", "sample.wav", "audio", "audio/wav", duration_seconds=5)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(again["status"], "budget_exhausted")
        self.assertNotIn("private-do-not-expose", str(result))
        self.assertEqual(post.await_count, 1)

    async def test_legacy_transport_is_also_bounded_without_automatic_resubmission(self):
        async def pending(*_args, **_kwargs):
            await asyncio.Event().wait()
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v2"}), \
             patch.object(hive_service, "HIVE_REQUEST_TIMEOUT_SECONDS", .01), \
             patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=pending)) as post:
            result = await asyncio.wait_for(hive_service.check_hive_media(b"legacy-control"), timeout=1)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(post.await_count, 1)

    async def test_media_image_audio_and_sampled_video_reserve_fifty_seconds_only_for_hive(self):
        observed = []
        def job(name):
            async def result(*_args, **_kwargs):
                return {"label": name, "available": False}
            return result
        async def layer(coro, timeout):
            result = await coro
            observed.append((result["label"], timeout))
            return result
        with ExitStack() as stack:
            for name, label in {"check_deepfake": "sightengine", "check_ai_image_hf": "hf",
                                "check_hive_media": "hive", "analyze_audio_quick_for_demonstration": "asr",
                                "detect_synthetic_speech": "speech"}.items():
                stack.enter_context(patch.object(media_analysis, name, side_effect=job(label)))
            stack.enter_context(patch.object(media_analysis, "prepare_speech_input", new=AsyncMock(return_value=(b"local", False, "success"))))
            stack.enter_context(patch.object(media_analysis, "safe_layer", side_effect=layer))
            stack.enter_context(patch.object(media_analysis, "hive_v3_enabled", return_value=True))
            stack.enter_context(patch.object(media_analysis, "extract_video_frames", new=AsyncMock(return_value=[(1, b"frame"), (2, b"frame"), (3, b"frame")])))
            await media_analysis.image_layers(b"image", "image/png", "image.png", auxiliary=False)
            await media_analysis.audio_layers(b"speech", "audio/wav", duration_seconds=1)
            await media_analysis.video_visual_layers(ValidatedMedia(b"video", "video.mp4", "video/mp4", "video", {"duration_seconds": 5}))
        self.assertEqual([timeout for name, timeout in observed if name == "hive"], [50] * 5)
        self.assertTrue(all(timeout == 18 for name, timeout in observed if name in {"sightengine", "hf", "speech"}))


if __name__ == "__main__":
    unittest.main()
