"""Local silence admission, not a speech/authenticity accuracy benchmark."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import helpers  # disables dotenv/provider credentials before application imports
from app.services.media_analysis import audio_layers, analyze_media
from app.services.media_validation import ValidatedMedia


class AudioSignalGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_decoded_silent_wav_never_calls_acoustic_detectors(self):
        audio = {"transcription": "", "transcription_status": "no_speech"}
        with patch("app.services.media_analysis.check_hive_media", new=AsyncMock()) as hive, \
             patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock()) as sight, \
             patch("app.services.media_analysis.analyze_audio_quick_for_demonstration", new=AsyncMock(return_value=audio)):
            result = await audio_layers(helpers.valid_wav(), "audio/wav", duration_seconds=1)
        hive.assert_not_awaited()
        sight.assert_not_awaited()
        self.assertIs(result["audio"], audio)
        for name in ("hive", "sightengine_audio"):
            self.assertFalse(result[name]["available"])
            self.assertEqual(result[name]["status"], "insufficient_signal")
            self.assertEqual(result[name]["decision_role"], "local_signal_gate")
            self.assertIn("não determina autenticidade nem falsidade", result[name]["reason"])

    async def test_successful_non_silent_observation_preserves_speech_detector_input(self):
        original = b"original-authorized-speech-control"
        prepared = b"private-mono-copy-not-to-be-forwarded"
        hive_result = {"available": True, "status": "success", "ai_generated_score": .9}
        sight_result = {"available": False, "status": "disabled"}
        with patch("app.services.media_analysis.prepare_speech_input", new=AsyncMock(return_value=(prepared, False, "success"))) as gate, \
             patch("app.services.media_analysis.analyze_audio_quick_for_demonstration", new=AsyncMock(return_value={"transcription": "Não envie dinheiro."})), \
             patch("app.services.media_analysis.check_hive_media", new=AsyncMock(return_value=hive_result)) as hive, \
             patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock(return_value=sight_result)) as sight:
            result = await audio_layers(original, "audio/ogg", duration_seconds=4.2)
        gate.assert_awaited_once_with(original)
        hive.assert_awaited_once_with(original, "evidence.ogg", "audio", "audio/ogg", duration_seconds=4.2)
        sight.assert_awaited_once_with(original, "audio/ogg")
        self.assertEqual(result["hive"], hive_result)
        self.assertEqual(result["sightengine_audio"], sight_result)

    async def test_gate_failure_or_unknown_status_does_not_invent_silence(self):
        for observation in (ValueError("local decoder unavailable"), asyncio.TimeoutError(),
                            (b"control", None, "unavailable"), (b"control", True, "unavailable")):
            with self.subTest(observation=str(observation)), \
                 patch("app.services.media_analysis.prepare_speech_input", new=AsyncMock(**(
                     {"side_effect": observation} if isinstance(observation, Exception) else {"return_value": observation}))), \
                 patch("app.services.media_analysis.analyze_audio_quick_for_demonstration", new=AsyncMock(return_value={})), \
                 patch("app.services.media_analysis.check_hive_media", new=AsyncMock(return_value={"available": False, "status": "disabled"})) as hive, \
                 patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock(return_value={"available": False, "status": "disabled"})) as sight:
                result = await audio_layers(b"validated-control", "audio/wav", duration_seconds=1)
            hive.assert_awaited_once()
            sight.assert_awaited_once()
            self.assertNotEqual(result["hive"]["status"], "insufficient_signal")

    async def test_cancellation_during_gate_does_not_start_detectors(self):
        with patch("app.services.media_analysis.prepare_speech_input", new=AsyncMock(side_effect=asyncio.CancelledError())), \
             patch("app.services.media_analysis.analyze_audio_quick_for_demonstration", new=AsyncMock(return_value={})), \
             patch("app.services.media_analysis.check_hive_media", new=AsyncMock()) as hive, \
             patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock()) as sight:
            with self.assertRaises(asyncio.CancelledError):
                await audio_layers(b"validated-control", "audio/wav", duration_seconds=1)
        hive.assert_not_awaited()
        sight.assert_not_awaited()

    async def test_silent_report_preserves_media_metadata_without_authenticity_claim(self):
        details = {"duration_seconds": 1, "has_audio": True, "has_video": False}
        media = ValidatedMedia(helpers.valid_wav(), "quiet.wav", "audio/wav", "audio", details)
        with patch("app.services.media_analysis.check_hive_media", new=AsyncMock()) as hive, \
             patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock()) as sight:
            report = await analyze_media(media, review_first=True)
        hive.assert_not_awaited()
        sight.assert_not_awaited()
        self.assertEqual(report["media_details"], details)
        self.assertEqual(report["query_input"], "quiet.wav")
        self.assertEqual(report["transcription"], "")
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["authenticity_status"], "undetermined")
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertNotEqual(report["verdict"], "Authentic")
        self.assertEqual(report["provider_coverage"]["hive"]["status"], "insufficient_signal")
        self.assertEqual(report["provider_coverage"]["transcription"]["status"], "no_speech")


if __name__ == "__main__":
    unittest.main()
