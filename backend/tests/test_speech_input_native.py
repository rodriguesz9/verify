"""Native normalized PCM inspection; no remote service or subprocess needed."""
import io
import unittest
import wave
from unittest.mock import AsyncMock, patch

import helpers
from app.services import speech_input


def wav(pcm, rate=16000, channels=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm)
    return output.getvalue()


class NativePcmTests(unittest.IsolatedAsyncioTestCase):
    async def test_normalized_silent_wav_does_not_depend_on_subprocess_or_ffmpeg(self):
        data = wav(b"\0\0" * 16000)
        with patch.object(speech_input.shutil, "which", return_value=None), \
             patch.object(speech_input, "run_media_tool", new=AsyncMock()) as tool:
            output, silent, status = await speech_input.prepare_speech_input(data)
        tool.assert_not_awaited()
        self.assertTrue(silent)
        self.assertEqual(status, "success")
        with wave.open(io.BytesIO(output), "rb") as audio:
            self.assertEqual(audio.readframes(16001), b"\0\0" * 16000)

    async def test_non_silent_pcm_remains_non_silent_without_a_remote_authenticity_claim(self):
        data = wav(b"\x00\x10" * 1600)
        with patch.object(speech_input, "run_media_tool", new=AsyncMock()) as tool:
            _, silent, status = await speech_input.prepare_speech_input(data)
        tool.assert_not_awaited()
        self.assertFalse(silent)
        self.assertEqual(status, "success")

    async def test_other_rate_or_channels_use_existing_bounded_decoder(self):
        for rate, channels in ((8000, 1), (16000, 2)):
            with self.subTest(rate=rate, channels=channels), \
                 patch.object(speech_input.shutil, "which", return_value="/usr/bin/ffmpeg"), \
                 patch.object(speech_input, "run_media_tool", new=AsyncMock(return_value=b"\x00\x10" * 1600)) as tool:
                _, silent, status = await speech_input.prepare_speech_input(wav(b"\0\0" * 1600, rate, channels))
            tool.assert_awaited_once()
            self.assertEqual(tool.await_args.kwargs["timeout"], 3)
            self.assertFalse(silent)
            self.assertEqual(status, "success")

    async def test_truncated_or_malformed_wave_never_becomes_native_silence(self):
        for data in (wav(b"\0\0" * 1600)[:-1], b"RIFFinvalid", b"not-a-wave"):
            with self.subTest(size=len(data)), \
                 patch.object(speech_input.shutil, "which", return_value=None):
                output, silent, status = await speech_input.prepare_speech_input(data)
            self.assertEqual(output, data)
            self.assertIsNone(silent)
            self.assertEqual(status, "unavailable")
