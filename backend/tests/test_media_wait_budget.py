"""Scaled media waits/cancellation, never provider calls or accuracy claims."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers  # disables dotenv/provider credentials before application imports
import httpx
from fastapi import HTTPException
from app.services import hive_service, media_analysis, speech_detector
from app.services.media_validation import ValidatedMedia


class MediaWaitBudgetTests(unittest.IsolatedAsyncioTestCase):
    def video(self):
        return ValidatedMedia(b"local-decoding-control", "control.mp4", "video/mp4", "video",
                              {"duration_seconds": 120})

    async def test_nine_sequential_frames_can_finish_after_the_old_total_budget(self):
        # Scale seconds to hundredths: nine 3-second frame decodes take 27
        # seconds, beyond the old 20-second envelope but inside the new total.
        real_wait_for = asyncio.wait_for
        deadlines = []

        async def scaled_wait(coro, timeout):
            deadlines.append(timeout)
            return await real_wait_for(coro, timeout=timeout / 100)

        async def decode(*_args, **_kwargs):
            await asyncio.sleep(.03)
            return b"decoded-frame-control"

        with patch.dict(os.environ, {"VIDEO_MAX_FRAMES": "9"}), \
             patch("app.services.media_validation.shutil.which", return_value="/local/ffmpeg"), \
             patch("app.services.media_validation.run_media_tool", new=AsyncMock(side_effect=decode)) as tool, \
             patch.object(media_analysis.asyncio, "wait_for", side_effect=scaled_wait), \
             patch.object(media_analysis, "image_layers", new=AsyncMock(return_value={})) as detectors:
            frames, results = await media_analysis.video_visual_layers(self.video())
        self.assertEqual(deadlines, [90.0])
        self.assertEqual(len(frames), 9)
        self.assertEqual(len(results), 9)
        self.assertEqual(tool.await_count, 9)
        self.assertEqual(detectors.await_count, 9)

    async def _cancel_extraction(self, *, caller_cancels):
        class PendingProcess:
            def __init__(self):
                self.returncode = None
                self.started = asyncio.Event()
                self.killed = 0
                self.communications = 0

            async def communicate(self):
                self.communications += 1
                if self.returncode is None:
                    self.started.set()
                    await asyncio.Event().wait()
                return b"", b""

            def kill(self):
                self.killed += 1
                self.returncode = -9

        process = PendingProcess()
        with patch("app.services.media_validation.shutil.which", return_value="/local/ffmpeg"), \
             patch("app.services.media_validation.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)), \
             patch.object(media_analysis, "VIDEO_FRAME_EXTRACTION_TIMEOUT_SECONDS", .05), \
             patch.object(media_analysis, "image_layers", new=AsyncMock()) as detectors:
            task = asyncio.create_task(media_analysis.video_visual_layers(self.video()))
            await process.started.wait()
            if caller_cancels:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            else:
                with self.assertRaises(HTTPException) as raised:
                    await task
                self.assertEqual(raised.exception.status_code, 504)
            detectors.assert_not_awaited()
            self.assertTrue(task.done())
        self.assertEqual(process.killed, 1)
        self.assertEqual(process.communications, 2)
        self.assertEqual(process.returncode, -9)

    async def test_frame_total_deadline_kills_and_reaps_decoder_before_returning(self):
        await self._cancel_extraction(caller_cancels=False)

    async def test_caller_cancellation_kills_and_reaps_decoder_without_detectors(self):
        await self._cancel_extraction(caller_cancels=True)

    async def test_provider_failure_status_survives_layer_wait_without_resubmission(self):
        env = {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-only",
               "HIVE_V3_MEDIA_TYPES": "image", "HIVE_V3_IMAGE_REQUEST_LIMIT": "1"}
        for response, expected in (
            (httpx.Response(503), "unavailable"),
            (httpx.Response(202), "pending"),
            (httpx.Response(200, json={"model": hive_service.HIVE_V3_MODEL,
                                     "output": [{"classes": [{"class": "ai_generated", "value": "invalid"}]}]}),
             "invalid_response"),
        ):
            with self.subTest(status=expected), patch.dict(os.environ, env), \
                 patch.object(hive_service, "hive_v3_budget", hive_service.HiveV3Budget()), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
                result = await media_analysis.safe_layer(hive_service.check_hive_media(b"fixed-control"), timeout=1)
                again = await hive_service.check_hive_media(b"fixed-control")
            self.assertFalse(result["available"])
            self.assertEqual(result["status"], expected)
            self.assertEqual(again["status"], "budget_exhausted")
            self.assertEqual(post.await_count, 1)

    async def test_speech_failure_and_bad_schema_remain_distinct_from_expired_wait(self):
        env = {"SIGHTENGINE_AUDIO_ENABLED": "true", "SIGHTENGINE_API_USER": "test-only",
               "SIGHTENGINE_API_SECRET": "test-only"}
        for response, expected in (
            (httpx.Response(503), "error"),
            (httpx.Response(200, json={"status": "success", "type": {"ai_speech": "invalid"}}),
             "invalid_response"),
        ):
            with self.subTest(status=expected), patch.dict(os.environ, env), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
                result = await media_analysis.safe_layer(speech_detector.detect_synthetic_speech(b"fixed-control"), timeout=1)
            self.assertEqual(result["status"], expected)
            self.assertFalse(result["available"])
            self.assertEqual(post.await_count, 1)


if __name__ == "__main__":
    unittest.main()
