import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from helpers import app, FakeSession, fake_user, override_auth_and_db, valid_png, valid_wav
from app.services.media_validation import validate_media, extract_video_frames, extract_video_audio, run_media_tool, ValidatedMedia, MAX_BYTES
from app.services.media_analysis import analyze_media
from app.services.evidence_policy import media_report
from app.services.c2pa_service import _scan_binary_c2pa_markers, parse_c2pa_report
from app.services.audio_service import analyze_audio_quick_for_demonstration
from app.services.gemini_service import consolidate_forensic_report
from app.core.pipeline import extract_source_from_url, _merge_verdicts
from app.core.pipeline import run_pipeline


class MediaPolicyTests(unittest.TestCase):
    def test_absent_providers_are_not_authentic(self):
        report = media_report({})
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertNotEqual(report["verdict"], "Authentic")
        self.assertIsNone(report["confidence"])

    def test_zero_detection_is_not_proof_of_authenticity(self):
        self.assertEqual(media_report({"sightengine": {"available": True, "genai_probability": 0}})["analysis_status"], "inconclusive")

    def test_one_strong_detector_is_not_consensus(self):
        self.assertEqual(media_report({"hive": {"available": True, "ai_generated_score": .99}})["verdict"], "Suspicious")

    def test_two_strong_detectors_show_indications_not_certainty(self):
        report = media_report({"hive": {"available": True, "ai_generated_score": .96},
                              "sightengine": {"available": True, "genai_probability": .95}})
        self.assertEqual(report["verdict"], "AI_Generated")
        self.assertEqual(report["analysis_status"], "partial")
        self.assertIsNone(report["confidence"])

    def test_conflicting_detectors_require_manual_review(self):
        report = media_report({"hive": {"available": True, "ai_generated_score": .96},
                              "sightengine": {"available": True, "genai_probability": .95},
                              "huggingface": {"available": True, "ai_probability": .04}})
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_error_scores_and_nonfinite_values_are_not_evidence(self):
        for value in (float("nan"), float("inf"), -1, 2, True, "0.99"):
            with self.subTest(value=value):
                report = media_report({"hive": {"available": True, "ai_generated_score": value},
                                      "sightengine": {"available": True, "status": "error", "genai_probability": .99}})
                self.assertEqual(report["analysis_status"], "inconclusive")

    def test_forged_camera_metadata_never_proves_authenticity(self):
        report = media_report({"metadata": {"camera_make": "Canon", "date_original": "2010:01:01"}})
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_c2pa_created_action_is_not_ai_generation(self):
        report = _scan_binary_c2pa_markers(b"c2pa.actions.created jumb")
        self.assertFalse(report["generative_ai_flag"])

    def test_unverified_binary_ai_string_is_not_a_valid_credential(self):
        report = media_report({"c2pa": _scan_binary_c2pa_markers(b"c2pa trainedAlgorithmicMedia")})
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_c2pa_resolves_active_manifest_id_and_requires_trust(self):
        data = {"active_manifest": "id", "manifests": {"id": {"assertions": [{"label": "c2pa.actions", "data": {"digitalSourceType": "trainedAlgorithmicMedia"}}]}}, "validation_status": []}
        self.assertEqual(parse_c2pa_report(data)["validation_state"], "present_unverified_trust")
        self.assertFalse(parse_c2pa_report(data)["generative_ai_flag"])
        self.assertTrue(parse_c2pa_report(data, True)["generative_ai_flag"])
        data["validation_status"] = [{"code": "claimSignature.mismatch"}]
        self.assertFalse(parse_c2pa_report(data, True)["generative_ai_flag"])

    def test_trusted_domain_substring_spoofing_is_rejected(self):
        for url in ("https://gov.br.evil.example", "https://fakebbc.example", "https://reuters.com.evil.example"):
            self.assertFalse(extract_source_from_url(url)["is_trusted"])
        self.assertTrue(extract_source_from_url("https://www.gov.br")["is_trusted"])

    def test_llm_agreement_does_not_invent_accuracy_boost(self):
        report = _merge_verdicts({"verdict": "Authentic", "score": 70}, {"verdict": "Authentic", "score": 95})
        self.assertEqual(report["score"], 70)


class AsyncMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_text_pipeline_without_mocked_providers(self):
        result = await run_pipeline("Pague uma taxa para liberar seu Pix imediatamente!")
        self.assertIn("report", result)
        self.assertNotEqual(result["report"]["verdict"], "Authentic")
        self.assertIsNone(result["metrics"]["text_ai_probability"])

    async def test_empty_and_oversized_files(self):
        for data, code in ((b"", 422), (b"x" * (MAX_BYTES + 1), 413)):
            with self.assertRaises(HTTPException) as caught:
                await validate_media(data)
            self.assertEqual(caught.exception.status_code, code)

    async def test_invalid_and_spoofed_image_uploads(self):
        for data, mime, code in ((b"not pixels", "image/png", 422), (valid_png(), "audio/wav", 415),
                                 (b"\x89PNG\r\n\x1a\nBAD", "image/png", 422), (b"%PDF-example", "application/pdf", 415)):
            with self.assertRaises(HTTPException) as caught:
                await validate_media(data, "fake.png", mime)
            self.assertEqual(caught.exception.status_code, code)

    async def test_neutral_filename_is_inferred_from_pixels(self):
        media = await validate_media(valid_png(), "../../safe.bin", "application/octet-stream")
        self.assertEqual(media.kind, "image")
        self.assertEqual(media.filename, "safe.bin")

    async def test_valid_mp4_extracts_three_real_decodable_frames(self):
        data = (Path(__file__).parent / "fixtures/synthetic-cafe.mp4").read_bytes()
        media = await validate_media(data, "neutral.mp4", "video/mp4")
        frames = await extract_video_frames(media)
        self.assertEqual(len(frames), 3)
        for timestamp, image in frames:
            self.assertGreater(timestamp, 0)
            self.assertEqual((await validate_media(image)).kind, "image")

    async def test_long_video_requests_nine_distinct_timestamps(self):
        media = ValidatedMedia(b"synthetic-control", "neutral.mp4", "video/mp4", "video", {"duration_seconds": 120})
        with patch.dict(os.environ, {"VIDEO_MAX_FRAMES": "9"}), \
             patch("app.services.media_validation.run_media_tool", new=AsyncMock(return_value=valid_png())):
            frames = await extract_video_frames(media)
        self.assertEqual(len(frames), 9)
        self.assertEqual([t for t, _ in frames], [12, 24, 36, 48, 60, 72, 84, 96, 108])

    async def test_real_video_track_extraction_preserves_audio_without_voice_claim(self):
        # Generated tone is a decoding control, never a genuine/clone benchmark.
        with tempfile.TemporaryDirectory(prefix="verify-tone-test-") as directory:
            path = Path(directory) / "tone.mp4"
            await run_media_tool("ffmpeg", "-v", "error", "-nostdin", "-threads", "1", "-f", "lavfi",
                "-i", "color=c=blue:s=64x64:r=5:d=1", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(path))
            media = await validate_media(path.read_bytes(), "neutral.mp4", "video/mp4")
        self.assertTrue(media.details["has_audio"])
        track = await extract_video_audio(media)
        self.assertEqual((await validate_media(track, "track.wav", "audio/wav")).kind, "audio")
        report = await analyze_media(media)
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["audio_analysis"]["authenticity_status"], "undetermined")

    async def test_cross_frame_means_cannot_create_consensus(self):
        media = ValidatedMedia(b"control", "neutral.mp4", "video/mp4", "video", {"duration_seconds": 120})
        # Every frame has two highs but also a contradicting third detector.
        names = [("sightengine", "genai_probability"), ("hive", "ai_generated_score"), ("huggingface", "ai_probability")]
        results = [{name: {"available": True, "status": "success", field: .2 if i % 3 == j else 1.0}
                    for j, (name, field) in enumerate(names)} for i in range(9)]
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=(
                [(i, b"frame") for i in range(9)], results))):
            report = await analyze_media(media)
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertTrue(report["detector_disagreement"])
        self.assertFalse(report["flagged_timestamps_seconds"])
        self.assertTrue(all(item["ai_score"] is None for item in report["provider_coverage"].values()))

    async def test_video_audio_indications_do_not_relabel_facial_manipulation(self):
        media = ValidatedMedia(b"control", "neutral.mp4", "video/mp4", "video",
                               {"duration_seconds": 1, "has_audio": True})
        frame = {"sightengine": {"available": True, "deepfake_probability": .99},
                 "hive": {"available": True, "deepfake_score": .99}}
        track = media_report({"hive": {"available": True, "ai_generated_score": .99},
                              "sightengine_audio": {"available": True, "ai_speech_score": .99}}, "audio")
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=([(0.5, b"frame")], [frame]))), \
             patch("app.services.media_analysis.video_audio_layers", new=AsyncMock(return_value=track)):
            report = await analyze_media(media)
        self.assertEqual(report["verdict"], "Manipulated")
        self.assertEqual(report["authenticity_status"], "manipulation_indications")
        self.assertEqual(report["audio_analysis"]["authenticity_status"], "ai_indications")

    async def test_later_facial_frame_is_not_hidden_by_earlier_ai_frame(self):
        media = ValidatedMedia(b"control", "neutral.mp4", "video/mp4", "video", {"duration_seconds": 3})
        generated = {"sightengine": {"available": True, "genai_probability": .99},
                     "hive": {"available": True, "ai_generated_score": .99}}
        facial = {"sightengine": {"available": True, "deepfake_probability": .99},
                  "hive_deepfake": {"available": True, "deepfake_score": .99}}
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=(
                [(0.3, b"frame"), (1.5, b"frame"), (2.7, b"frame")], [generated, {}, facial]))):
            report = await analyze_media(media)
        self.assertEqual(report["verdict"], "Manipulated")
        self.assertEqual(report["flagged_timestamps_seconds"], [.3, 2.7])

    async def test_corrupted_mp4_is_rejected(self):
        with self.assertRaises(HTTPException):
            await validate_media(b"\x00\x00\x00\x18ftypmp42broken", "video.mp4", "video/mp4")

    async def test_audio_rename_never_changes_voice_verdict(self):
        with patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock(return_value="")):
            results = [await analyze_audio_quick_for_demonstration(valid_wav(), name) for name in
                       ("humana.wav", "fake_clonado.wav", "normal.wav")]
        self.assertEqual({r["verdict"] for r in results}, {"inconclusiva"})
        self.assertTrue(all(r["transcription"] == "" and r["confidence"] is None for r in results))

    async def test_scam_transcript_is_not_evidence_of_voice_cloning(self):
        with patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock(return_value="Mãe perdi meu celular faz um pix urgente")):
            report = await analyze_audio_quick_for_demonstration(valid_wav(), "normal.wav")
        self.assertEqual(report["verdict"], "inconclusiva")
        self.assertTrue(report["content_risk"]["is_scam_pattern"])
        self.assertFalse(any("espectral" in item.lower() for item in report["indicators"]))

    async def test_no_key_consolidation_is_not_authentic(self):
        report = await consolidate_forensic_report("real.jpg", {}, {}, {}, {})
        self.assertEqual(report["veredito_final"], "inconclusivo")


class MediaEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()
        override_auth_and_db(fake_user(), self.db)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_all_upload_endpoints_reject_empty_and_corrupt_data(self):
        for endpoint in ("/upload", "/verificar/completo", "/verificar/audio-rapido", "/capturar/selo", "/verificar/selo", "/verificar/relatorio-pdf"):
            for data in (b"", b"FAKE_BYTES"):
                with self.subTest(endpoint=endpoint, data=data):
                    response = self.client.post("/api" + endpoint, files={"file": ("sample.png", data, "image/png")})
                    self.assertEqual(response.status_code, 422)

    def test_full_video_flow_returns_sampling_and_not_filename_analysis(self):
        video = (Path(__file__).parent / "fixtures/synthetic-cafe.mp4").read_bytes()
        with patch("app.api.verificacao.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/verificar/completo", files={"file": ("video.mp4", video, "video/mp4")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["forensics"]["video"]["sampled_frames"], 3)
        self.assertEqual(response.json()["analysis_status"], "inconclusive")

    def test_quick_audio_endpoint_exposes_actual_acoustic_indications(self):
        with patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock(return_value={"available": True, "status": "success", "ai_speech_score": .98})), \
             patch("app.services.media_analysis.check_hive_media", new=AsyncMock(return_value={"available": True, "status": "success", "ai_generated_score": .97})):
            response = self.client.post("/api/verificar/audio-rapido", files={"file": ("neutral.wav", valid_wav(), "audio/wav")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verdict"], "indicios_sintetica")
        self.assertIsNone(response.json()["score_percent"])
        self.assertEqual(response.json()["veracity_status"], "unverified")

    def test_pdf_handles_markup_in_filename(self):
        with patch("app.api.verificacao.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/verificar/relatorio-pdf", files={"file": ("<broken>.png", valid_png(), "image/png")})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
