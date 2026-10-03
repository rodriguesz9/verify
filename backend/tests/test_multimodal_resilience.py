import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from helpers import valid_png
from app.core.audio_checker import transcribe_and_extract_audio
from app.core.gemini_client import GeneratedText, GeminiError, generate_text
from app.core.gemini_analyzer import extract_text_from_image
from app.services.evidence_policy import media_report
from app.services.local_ocr import _parse_tsv, _prepare_image, extract_local_text


class MultimodalResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_silence_gate_skips_both_providers(self):
        from app.services.audio_service import analyze_audio_quick_for_demonstration
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASSEMBLYAI_API_KEY": "test"}), \
             patch("app.services.speech_input.prepare_speech_input", new=AsyncMock(return_value=(b"silent", True, "success"))), \
             patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock()) as gemini, \
             patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock()) as assembly:
            result = await analyze_audio_quick_for_demonstration(b"silent")
        self.assertEqual(result["transcription_detail"]["status"], "no_speech")
        self.assertEqual(result["transcription"], "")
        gemini.assert_not_awaited(); assembly.assert_not_awaited()

    async def test_preferred_assembly_success_skips_gemini(self):
        from app.services.audio_service import analyze_audio_quick_for_demonstration
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "ASSEMBLYAI_API_KEY": "test", "AUDIO_TRANSCRIPTION_PROVIDER": "assemblyai"}), \
             patch("app.services.speech_input.prepare_speech_input", new=AsyncMock(return_value=(b"voice", False, "success"))), \
             patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock()) as gemini, \
             patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock(return_value={"available": True, "status": "success", "transcription": "Olá mundo", "model_used": "universal-2"})):
            result = await analyze_audio_quick_for_demonstration(b"voice")
        self.assertEqual(result["transcription_provider"], "assemblyai")
        gemini.assert_not_awaited()

    async def test_absent_fallback_preserves_pending_assembly_reason(self):
        from app.services.audio_service import analyze_audio_quick_for_demonstration
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "ASSEMBLYAI_API_KEY": "test", "AUDIO_TRANSCRIPTION_PROVIDER": "assemblyai"}), \
             patch("app.services.speech_input.prepare_speech_input", new=AsyncMock(return_value=(b"voice", False, "success"))), \
             patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock(return_value={"available": False, "status": "pending", "reason": "Job pendente"})):
            result = await analyze_audio_quick_for_demonstration(b"voice")
        self.assertEqual(result["transcription_detail"]["status"], "pending")
        self.assertEqual(result["transcription_detail"]["reason"], "Job pendente")
        self.assertEqual(result["transcription"], "")

    def test_safety_warning_and_urgency_alone_not_financial_scam(self):
        from app.core.scam_detector import analyze_scam_indicators
        from app.services.audio_service import detect_acoustic_scam_heuristics
        self.assertFalse(analyze_scam_indicators("Nao pague uma taxa para liberar seu Pix.")["is_scam"])
        self.assertTrue(analyze_scam_indicators("Pague uma taxa para liberar seu Pix.")["is_scam"])
        self.assertTrue(analyze_scam_indicators("Não pague taxa. Mas pague uma taxa para liberar Pix.")["is_scam"])
        for text in ("É urgente chegar à aula.", "Mãe, não faça um Pix urgente."):
            self.assertFalse(detect_acoustic_scam_heuristics(text, b"control")["is_scam_pattern"])

    async def test_local_ocr_success_skips_all_cloud_calls(self):
        local = {"available": True, "status": "success", "provider": "tesseract", "text": "Controle impresso"}
        with patch("app.services.local_ocr.extract_local_text", new=AsyncMock(return_value=local)), \
             patch("app.core.gemini_analyzer.generate_text", new=AsyncMock()) as gemini, \
             patch("app.core.openrouter_service.extract_image_text", new=AsyncMock()) as router:
            result = await extract_text_from_image(valid_png(), "image/png")
        self.assertEqual(result, local)
        gemini.assert_not_awaited(); router.assert_not_awaited()

    async def test_local_ocr_not_installed_is_not_success(self):
        with patch.dict(os.environ, {"LOCAL_OCR_ENABLED": "true"}), patch("shutil.which", return_value=None):
            self.assertEqual((await extract_local_text(valid_png()))["status"], "not_installed")

    def test_local_ocr_rejects_invalid_image(self):
        with self.assertRaises(Exception):
            _prepare_image(b"not an image")

    def test_local_ocr_preserves_line_order_and_numbers(self):
        header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tconf\ttext\n"
        rows = "5\t1\t1\t1\t1\t1\t95\tNao\n5\t1\t1\t1\t1\t2\t96\tpague\n5\t1\t1\t1\t2\t1\t88\t123,45\n"
        self.assertEqual(_parse_tsv((header + rows).encode()), ("Nao pague\n123,45", True))
        self.assertFalse(_parse_tsv((header + rows.replace("95", "5").replace("96", "5").replace("88", "5")).encode())[1])
        self.assertEqual(_parse_tsv(header.encode()), ("", False))

    def test_local_ocr_invalid_scores_and_oversized_output_rejected(self):
        for value in (b"x" * 2_000_001, b"level\tconf\ttext\n5\tnan\tTexto\n"):
            with self.assertRaises(ValueError):
                _parse_tsv(value)

    async def test_explicit_media_model_does_not_rotate_global_fallback(self):
        response = httpx.Response(503)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "GEMINI_FALLBACK_MODELS": "gemini-3.7-flash"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            with self.assertRaises(GeminiError):
                await generate_text("controle", model_name="gemini-3.1-flash-lite")
        self.assertEqual(post.await_count, 1)
        self.assertIn("gemini-3.1-flash-lite:generateContent", post.call_args.args[0])

    async def test_invalid_model_blocked_before_request(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            with self.assertRaises(GeminiError):
                await generate_text("controle", model_name="wrong?key=private")
        post.assert_not_awaited()

    async def test_structured_transcript_and_silence_not_hallucinated(self):
        for value, expected in (('{"text":"Nao faça um Pix"}', "Nao faça um Pix"), ('{"text":""}', "")):
            generated = GeneratedText(value); generated.model_name = "control-model"
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "GEMINI_MEDIA_MODEL_NAME": "gemini-3.1-flash-lite"}), \
                 patch("app.core.audio_checker.generate_text", new=AsyncMock(return_value=generated)) as call:
                actual = await transcribe_and_extract_audio(b"control-bytes", "audio/wav")
            self.assertEqual(actual, expected)
            self.assertEqual(actual.model_name, "control-model")
            self.assertEqual(call.call_args.kwargs["response_schema"]["required"], ["text"])

    async def test_wrong_transcript_shape_not_accepted(self):
        generated = GeneratedText('{"text": true}'); generated.model_name = "control-model"
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), patch("app.core.audio_checker.generate_text", new=AsyncMock(return_value=generated)):
            with self.assertRaises(GeminiError) as raised:
                await transcribe_and_extract_audio(b"control")
        self.assertEqual(raised.exception.status, "invalid_response")

    def test_experimental_detector_visible_but_cannot_cast_decisive_vote(self):
        result = media_report({"sightengine": {"available": True, "status": "success", "genai_probability": .99},
            "huggingface": {"available": True, "status": "success", "ai_probability": .99, "voting_eligible": False,
                            "decision_role": "experimental_signal"}})
        self.assertEqual(result["analysis_status"], "inconclusive")
        self.assertEqual(result["provider_coverage"]["huggingface"]["ai_score"], .99)
        self.assertFalse(result["provider_coverage"]["huggingface"]["voting_eligible"])
        self.assertIsNone(result["authenticity_percentage"])
