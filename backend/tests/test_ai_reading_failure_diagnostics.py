"""Offline reading diagnostics and bounded technical fallbacks, never accuracy."""
from contextlib import ExitStack
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
from app.core import gemini_analyzer, pipeline
from app.core.gemini_client import GeminiError
from app.services import audio_service
from app.services.provider_diagnostics import provider_result_failure_metadata


class ReturnedDiagnosticsTests(unittest.TestCase):
    def test_result_metadata_recomputes_categories_and_drops_unknown_fields(self):
        result = provider_result_failure_metadata({"http_status": 503,
            "transport_failure": "private-marker", "response_issue": "token_limit",
            "provider_error_code": 429, "provider_failure": "private-marker",
            "headers": {"Authorization": "private-marker"}, "reasoning": "private-marker"})
        self.assertEqual(result, {"http_status": 503, "transport_failure": "provider_unavailable",
                                 "response_issue": "token_limit"})
        self.assertNotIn("private-marker", json.dumps(result))
        result = provider_result_failure_metadata({"response_issue": "provider_error", "provider_error_code": 429})
        self.assertEqual(result, {"response_issue": "provider_error", "provider_error_code": 429,
                                 "provider_failure": "provider_rate_limit"})
        for issue in ("invalid_json", "invalid_schema"):
            self.assertEqual(provider_result_failure_metadata({"response_issue": issue}), {"response_issue": issue})

    def test_unknown_invalid_or_wrong_typed_returned_fields_stay_private(self):
        for value in (None, [], "private-marker", {"http_status": True}, {"http_status": "503"},
                      {"response_issue": ["private-marker"]}, {"response_issue": "private-marker"},
                      {"provider_error_code": 429}, {"response_issue": "provider_error", "provider_error_code": "429"}):
            result = provider_result_failure_metadata(value)
            self.assertNotIn("private-marker", json.dumps(result))
            self.assertNotIn("provider_error_code", result)


class ReadingDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_extraction_retains_safe_failure_fields_without_output_or_extra_call(self):
        failure = GeminiError("Gemini indisponível (HTTP 503).", "unavailable", 503)
        failure.headers = {"Authorization": "private-marker"}
        with patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)) as generate:
            result = await gemini_analyzer.extract_claims_with_ai("O evento Alfa ocorreu em 2020.")
        self.assertEqual(result, [])
        self.assertEqual(result.coverage["http_status"], 503)
        self.assertEqual(result.coverage["transport_failure"], "provider_unavailable")
        self.assertNotIn("private-marker", json.dumps(result.coverage))
        generate.assert_awaited_once()

    async def test_claim_extraction_reports_content_block_without_fabricating_claims(self):
        failure = GeminiError("Solicitação bloqueada.", "invalid_response", response_issue="content_blocked")
        with patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)):
            result = await gemini_analyzer.extract_claims_with_ai("O evento Alfa ocorreu em 2020.")
        self.assertEqual(result, [])
        self.assertEqual(result.coverage["response_issue"], "content_blocked")
        self.assertFalse(result.coverage["available"])

    async def test_ocr_content_block_never_relays_image_to_openrouter(self):
        failure = GeminiError("Solicitação bloqueada.", "invalid_response", response_issue="content_blocked")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
             patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)), \
             patch("app.core.openrouter_service.extract_image_text", new=AsyncMock()) as alternate:
            result = await gemini_analyzer._extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertFalse(result["available"])
        self.assertEqual(result["response_issue"], "content_blocked")
        self.assertEqual(result["gemini_failure"], {"response_issue": "content_blocked"})
        alternate.assert_not_awaited()

    async def test_ocr_successful_technical_alternate_keeps_primary_failure_separate(self):
        failure = GeminiError("Gemini indisponível (HTTP 503).", "unavailable", 503)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
             patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)), \
             patch("app.core.openrouter_service.extract_image_text", new=AsyncMock(return_value={
                 "available": True, "status": "success", "text": "Não pague R$ 12,30.",
                 "provider": "openrouter", "decision_role": "ocr_only"})) as alternate:
            result = await gemini_analyzer._extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertTrue(result["available"])
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["text"], "Não pague R$ 12,30.")
        self.assertEqual(result["gemini_failure"], {"http_status": 503, "transport_failure": "provider_unavailable"})
        self.assertNotIn("http_status", result)
        alternate.assert_awaited_once()

    async def test_ocr_different_failures_have_distinct_sanitized_diagnostics(self):
        failure = GeminiError("Resposta truncada.", "invalid_response", response_issue="token_limit")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
             patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)), \
             patch("app.core.openrouter_service.extract_image_text", new=AsyncMock(return_value={
                 "available": False, "status": "rate_limited", "text": "", "http_status": 429,
                 "transport_failure": "private-marker", "response_issue": "provider_error",
                 "provider_error_code": 429})):
            result = await gemini_analyzer._extract_image_text_remote(helpers.valid_png(), "image/png")
        self.assertFalse(result["available"])
        self.assertEqual(result["response_issue"], "token_limit")
        self.assertEqual(result["fallback_failure"]["http_status"], 429)
        self.assertEqual(result["fallback_failure"]["transport_failure"], "provider_rate_limit")
        self.assertNotIn("private-marker", json.dumps(result))

    async def test_visual_inspection_retains_diagnostics_without_turning_failure_into_vote(self):
        failure = GeminiError("Resposta truncada.", "invalid_response", response_issue="token_limit")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
             patch.object(gemini_analyzer, "generate_text", new=AsyncMock(side_effect=failure)):
            result = await gemini_analyzer.analyze_image_with_vision(helpers.valid_png(), "image/png", {})
        self.assertFalse(result["available"])
        self.assertFalse(result["voting_eligible"])
        self.assertEqual(result["response_issue"], "token_limit")


class AudioFailureDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def run_audio(self, failure, alternate_result):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control", "ASSEMBLYAI_API_KEY": "offline-control",
                                     "AUDIO_TRANSCRIPTION_PROVIDER": "gemini"}), \
             patch("app.services.speech_input.prepare_speech_input", new=AsyncMock(return_value=(b"audio", False, "success"))), \
             patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock(side_effect=failure)), \
             patch.object(audio_service, "transcribe_with_assemblyai", new=AsyncMock(return_value=alternate_result)) as alternate:
            result = await audio_service.analyze_audio_quick_for_demonstration(b"audio", "control.wav", "audio/wav")
        return result, alternate

    async def test_content_block_does_not_resubmit_audio_to_assemblyai(self):
        result, alternate = await self.run_audio(GeminiError("Solicitação bloqueada.", "invalid_response",
            response_issue="content_blocked"), {"available": True, "status": "success", "transcription": "inventada"})
        self.assertEqual(result["transcription"], "")
        self.assertEqual(result["transcription_detail"]["response_issue"], "content_blocked")
        self.assertEqual(len(result["transcription_detail"]["attempts"]), 1)
        alternate.assert_not_awaited()

    async def test_technical_failure_uses_existing_asr_alternate_and_preserves_primary_attempt(self):
        result, alternate = await self.run_audio(GeminiError("Gemini indisponível (HTTP 503).", "unavailable", 503),
            {"available": True, "status": "success", "transcription": "Não pague R$ 12,30."})
        self.assertEqual(result["transcription"], "Não pague R$ 12,30.")
        self.assertEqual(result["transcription_provider"], "assemblyai")
        attempts = result["transcription_detail"]["attempts"]
        self.assertEqual(attempts[0]["http_status"], 503)
        self.assertEqual(attempts[0]["transport_failure"], "provider_unavailable")
        self.assertEqual(len(attempts), 2)
        alternate.assert_awaited_once()

    async def test_oversize_audio_rejection_does_not_trigger_another_provider(self):
        result, alternate = await self.run_audio(GeminiError("Arquivo grande demais.", "input_too_large"), {})
        self.assertEqual(result["transcription"], "")
        self.assertEqual(result["transcription_detail"]["status"], "input_too_large")
        alternate.assert_not_awaited()


class PipelineExtractionDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def run_pipeline(self, issue):
        text = "O evento Alfa ocorreu em 2020. O evento Beta ocorreu em 2021."
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"OPENROUTER_API_KEY": "offline-control", "OPENROUTER_ENABLED": "true"}))
            stack.enter_context(patch.object(pipeline, "_run_openrouter_check", new=AsyncMock(return_value={
                "available": False, "status": "invalid_response", "claims": [], "response_issue": issue,
                "http_status": 503, "transport_failure": "private-marker", "decision_role": "search_hints_only"})))
            extraction = stack.enter_context(patch.object(pipeline, "extract_claims_with_ai", new=AsyncMock(return_value=[])))
            stack.enter_context(patch.object(pipeline, "detect_ai_text", new=AsyncMock(return_value={})))
            facts = stack.enter_context(patch.object(pipeline, "query_fact_check_api", new=AsyncMock(return_value=[])))
            stack.enter_context(patch.object(pipeline, "search_news", new=AsyncMock(return_value=[])))
            stack.enter_context(patch.object(pipeline, "_retrieve_source_attribution", new=AsyncMock(return_value={
                "status": "not_found", "matches": [], "coverage": {}, "_documents": []})))
            result = await pipeline.run_pipeline(text, use_source_crosscheck=False)
        self.assertIn(text, [call.args[0] for call in facts.await_args_list])
        return result["report"], extraction

    async def test_content_block_skips_secondary_extraction_and_keeps_literal_path(self):
        result, extraction = await self.run_pipeline("content_blocked")
        extraction.assert_not_awaited()
        self.assertEqual(result["provider_coverage"]["openrouter"]["response_issue"], "content_blocked")
        self.assertEqual(result["provider_coverage"]["openrouter"]["transport_failure"], "provider_unavailable")
        self.assertNotIn("private-marker", json.dumps(result))

    async def test_technical_extraction_failure_still_uses_gemini_once(self):
        result, extraction = await self.run_pipeline("token_limit")
        extraction.assert_awaited_once()
        self.assertEqual(result["provider_coverage"]["openrouter"]["response_issue"], "token_limit")

    async def test_unknown_diagnostic_value_is_not_exported(self):
        for issue in ("private-marker", [], {}):
            result, extraction = await self.run_pipeline(issue)
            extraction.assert_awaited_once()
            self.assertNotIn("response_issue", result["provider_coverage"]["openrouter"])
            self.assertNotIn("private-marker", json.dumps(result))
