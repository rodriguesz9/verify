import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from helpers import app, FakeSession, fake_user, fake_report, override_auth_and_db, valid_png
from app.services import extracted_text_review as review
from app.services.evidence_policy import media_report
from app.services.media_analysis import analyze_media, extracted_content
from app.services.media_validation import ValidatedMedia
from app.services.pdf_snapshot import attach_pdf_snapshot, verify_pdf_snapshot
from app.core.security import decode_token
from jose import JWTError

ORIGINAL = "Não pague R$ 123,45 em 03/10/2026."


def source_report():
    return {**media_report({"ocr": {"text": ORIGINAL, "provider": "tesseract", "available": True, "status": "success"}}),
            "filename": "controle.png", "file_hash_sha256": hashlib.sha256(valid_png()).hexdigest(),
            "analyzed_at": "2026-10-04T19:00:00+00:00"}


class ReviewCapabilityTests(unittest.TestCase):
    def test_exact_provenance_no_original_mutation_and_boundary_expiry(self):
        original = source_report(); before = copy.deepcopy(original)
        issued = review.attach_text_review(original, now=1000)
        restored = review.verify_text_review(issued["text_review_token"], now=1899)
        self.assertEqual(original, before)
        self.assertEqual(restored["original_text"], ORIGINAL)
        self.assertEqual(restored["file_hash_sha256"], original["file_hash_sha256"])
        with self.assertRaises(HTTPException) as caught:
            review.verify_text_review(issued["text_review_token"], now=1900)
        self.assertEqual(caught.exception.status_code, 410)

    def test_same_account_required_and_anonymous_is_not_authentication(self):
        user = fake_user(); token = review.attach_text_review(source_report(), user, now=1000)["text_review_token"]
        self.assertEqual(review.verify_text_review(token, user, now=1001)["original_text"], ORIGINAL)
        for other in (None, fake_user()):
            with self.assertRaises(HTTPException) as caught:
                review.verify_text_review(token, other, now=1001)
            self.assertEqual(caught.exception.status_code, 403)
        anonymous = review.attach_text_review(source_report(), now=1000)["text_review_token"]
        self.assertEqual(review.verify_text_review(anonymous, now=1001)["original_text"], ORIGINAL)
        with self.assertRaises(JWTError):
            decode_token(anonymous)

    def test_tokens_not_interchangeable_with_pdf(self):
        report = source_report()
        pdf = attach_pdf_snapshot(report)["pdf_snapshot_token"]
        token = review.attach_text_review(report)["text_review_token"]
        with self.assertRaises(HTTPException):
            review.verify_text_review(pdf)
        with self.assertRaises(HTTPException):
            verify_pdf_snapshot(token)

    def test_tampered_original_rejected_before_json_decode(self):
        prefix, encoded, signature = review.attach_text_review(source_report(), now=1000)["text_review_token"].split(".")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        payload["source"]["original_text"] = "Pague R$ 9999 agora."
        changed = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        with patch.object(review.json, "loads", side_effect=AssertionError("Parsed unverified input")):
            with self.assertRaises(HTTPException) as caught:
                review.verify_text_review(f"{prefix}.{changed}.{signature}", now=1001)
        self.assertEqual(caught.exception.status_code, 422)

    def test_missing_key_and_no_readable_text_are_not_ready(self):
        with patch.object(review, "_KEY", None):
            self.assertEqual(review.attach_text_review(source_report())["text_review_status"], "unavailable")
            with self.assertRaises(HTTPException) as caught:
                review.verify_text_review("anything")
            self.assertEqual(caught.exception.status_code, 503)
        for value in ("", "curto", "x" * 5001):
            report = source_report(); report["forensics"]["ocr"]["text"] = value
            self.assertEqual(review.attach_text_review(report)["text_review_status"], "unavailable")

    def test_invalid_and_oversized_tokens_fail_before_decode(self):
        for token in (None, {}, "vrev1.bad.bad", "x" * (review.MAX_REVIEW_TOKEN_BYTES + 1)):
            with patch.object(review.base64, "b64decode", side_effect=AssertionError("Unsafe decode")):
                with self.assertRaises(HTTPException):
                    review.verify_text_review(token)


class ReviewEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession(); self.user = fake_user()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)
        self.addCleanup(self.client.close); self.addCleanup(app.dependency_overrides.clear)
        self.token = review.attach_text_review(source_report(), self.user)["text_review_token"]

    def test_confirmed_new_text_check_uses_literal_edit_preserves_source_and_normal_quota(self):
        changed = "Não pague R$ 321,54 em 04/10/2026."
        result = {"report": fake_report(veracity_status="unverified"), "metrics": {"text_ai_probability": None}}
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value=result)) as pipeline, \
             patch("app.api.check_text.verify_limit", new=AsyncMock()) as quota:
            response = self.client.post("/api/check-extracted-text", json={"text": changed, "review_token": self.token})
        self.assertEqual(response.status_code, 200)
        report = response.json()
        pipeline.assert_awaited_once_with(text=changed, use_ai_extraction=False,
                                         use_detailed_report=True, use_gemini_report=True)
        quota.assert_awaited_once_with(self.user, self.db, "TEXTUAL")
        self.assertEqual(report["content_type"], "text")
        self.assertEqual(report["text_review"]["original_text"], ORIGINAL)
        self.assertEqual(report["text_review"]["reviewed_text"], changed)
        self.assertTrue(report["text_review"]["changed"])
        self.assertEqual(report["text_review"]["status"], "user_confirmed")
        self.assertEqual(self.db.commits, 1)
        self.assertNotIn("text_review_token", self.db.added[0].raw_result)
        self.assertNotIn("pdf_snapshot_token", report)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unchanged_confirmation_identified_without_detector_reanalysis(self):
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value={"report": fake_report()})), \
             patch("app.api.check_text.verify_limit", new=AsyncMock()), \
             patch("app.services.media_analysis.analyze_media", new=AsyncMock(side_effect=AssertionError("Media called"))) as media:
            response = self.client.post("/api/check-extracted-text", json={"text": ORIGINAL, "review_token": self.token})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["text_review"]["changed"])
        media.assert_not_awaited()

    def test_invalid_expired_or_other_account_blocked_before_quota_and_provider(self):
        cases = (("invalid", 422), (review.attach_text_review(source_report(), self.user, now=1000)["text_review_token"], 410),
                 (review.attach_text_review(source_report(), fake_user())["text_review_token"], 403))
        with patch("app.api.check_text.run_pipeline", new=AsyncMock()) as pipeline, \
             patch("app.api.check_text.verify_limit", new=AsyncMock()) as quota:
            for token, expected in cases:
                response = self.client.post("/api/check-extracted-text", json={"text": ORIGINAL, "review_token": token})
                self.assertEqual(response.status_code, expected)
        quota.assert_not_awaited(); pipeline.assert_not_awaited()
        self.assertEqual(self.db.commits, 0)

    def test_html_empty_overlong_or_extra_unsigned_fields_rejected(self):
        with patch("app.api.check_text.run_pipeline", new=AsyncMock()) as pipeline:
            for text in ("   <b> </b>   ", "<b>Não pague a taxa para liberar Pix.</b>", "x" * 5001):
                self.assertEqual(self.client.post("/api/check-extracted-text", json={"text": text, "review_token": self.token}).status_code, 422)
            response = self.client.post("/api/check-extracted-text", json={"text": ORIGINAL, "review_token": self.token, "original_text": "forged"})
            self.assertEqual(response.status_code, 422)
        pipeline.assert_not_awaited()

    def test_review_preserves_literal_operators_ampersand_negation_and_amount(self):
        literal = "Não pague R$ 123,45 se 2 < 3 & 4 > 1."
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value={"report": fake_report()})) as pipeline, \
             patch("app.api.check_text.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-extracted-text", json={"text": literal, "review_token": self.token})
        self.assertEqual(response.status_code, 200)
        pipeline.assert_awaited_once_with(text=literal, use_ai_extraction=False,
                                         use_detailed_report=True, use_gemini_report=True)
        self.assertEqual(response.json()["query_input"], literal)
        self.assertEqual(response.json()["text_review"]["reviewed_text"], literal)

    def test_body_size_and_foreign_origin_blocked(self):
        with patch("app.api.check_text.run_pipeline", new=AsyncMock()) as pipeline:
            too_large = self.client.post("/api/check-extracted-text", content=b"x" * (review.MAX_REVIEW_BODY_BYTES + 1))
            foreign = self.client.post("/api/check-extracted-text", headers={"Origin": "https://foreign.example.test"}, json={"text": ORIGINAL, "review_token": self.token})
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(foreign.status_code, 403)
        pipeline.assert_not_awaited()

    def test_upload_review_capability_not_persisted_or_nested_in_pdf(self):
        report = source_report()
        with patch("app.api.upload.analyze_media", new=AsyncMock(return_value=report)) as analyzer, \
             patch("app.api.upload.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/upload", files={"file": ("controle.png", valid_png(), "image/png")}, data={"review_text": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(analyzer.call_args.kwargs["review_first"])
        result = response.json()
        self.assertEqual(result["text_review_status"], "ready")
        stored = self.db.added[0].raw_result
        self.assertNotIn("text_review_token", stored)
        self.assertNotIn("text_review_token", verify_pdf_snapshot(result["pdf_snapshot_token"], self.user))
        self.assertEqual(review.verify_text_review(result["text_review_token"], self.user)["original_text"], ORIGINAL)


class MediaReviewStageTests(unittest.IsolatedAsyncioTestCase):
    async def test_short_ocr_preserves_labels_and_numbers_without_fact_check_or_review_token(self):
        media = ValidatedMedia(valid_png(), "controle.png", "image/png", "image", {})
        for text in ("A", "NASA", "42", "R$ 5", "123,45", "Não"):
            for review_first in (False, True):
                with self.subTest(text=text, review_first=review_first), \
                     patch("app.services.media_analysis.image_layers", new=AsyncMock(return_value={
                         "ocr": {"text": text, "provider": "tesseract", "available": True, "status": "success"}})), \
                     patch("app.core.pipeline.run_pipeline", new=AsyncMock()) as pipeline:
                    report = await analyze_media(media, review_first=review_first)
                pipeline.assert_not_awaited()
                self.assertEqual(report["forensics"]["ocr"]["text"], text)
                self.assertEqual(report["forensics"]["ocr"]["status"], "success")
                self.assertEqual(report["content_analysis"]["analysis_status"], "inconclusive")
                self.assertEqual(report["content_analysis"]["veracity_status"], "unverified")
                self.assertEqual(report["content_analysis"]["summary"],
                                 "A leitura retornou apenas um trecho curto; confira com a imagem. "
                                 "Não há texto suficiente para checar uma afirmação.")
                attached = review.attach_text_review(report)
                self.assertEqual(attached["text_review_status"], "unavailable")
                self.assertNotIn("text_review_token", attached)
                self.assertEqual(attached["forensics"]["ocr"]["text"], text)

    async def test_missing_short_and_overlong_extraction_have_distinct_reasons(self):
        cases = (("   ", "Não houve texto utilizável"),
                 ("A", "apenas um trecho curto"),
                 ("x" * 5001, "ultrapassa o limite de 5000 caracteres"))
        for text, reason in cases:
            for review_first in (False, True):
                with self.subTest(length=len(text), review_first=review_first), \
                     patch("app.core.pipeline.run_pipeline", new=AsyncMock()) as pipeline:
                    result = await extracted_content(text, "ocr", review_first=review_first)
                pipeline.assert_not_awaited()
                self.assertEqual(result["analysis_status"], "inconclusive")
                self.assertIn(reason, result["summary"])

    async def test_image_review_stops_before_content_sources(self):
        media = ValidatedMedia(valid_png(), "controle.png", "image/png", "image", {})
        with patch("app.services.media_analysis.image_layers", new=AsyncMock(return_value={"ocr": {"text": ORIGINAL, "provider": "tesseract"}})), \
             patch("app.services.media_analysis.check_content", new=AsyncMock(side_effect=AssertionError("Checked before review"))) as check:
            report = await analyze_media(media, review_first=True)
        self.assertEqual(report["content_analysis"]["analysis_status"], "pending_user_review")
        self.assertEqual(report["content_analysis"]["claim_assessments"], [])
        check.assert_not_awaited()

    async def test_audio_review_preserves_asr_error_and_defers_fact_check(self):
        asr_error = "Mãe, faz um pic surgente, por favor."
        media = ValidatedMedia(b"control", "audio.wav", "audio/wav", "audio", {})
        with patch("app.services.media_analysis.audio_layers", new=AsyncMock(return_value={"audio": {"transcription": asr_error}})), \
             patch("app.services.media_analysis.check_content", new=AsyncMock()) as check:
            report = await analyze_media(media, review_first=True)
        self.assertEqual(report["transcription"], asr_error)
        self.assertEqual(report["content_analysis"]["analysis_status"], "pending_user_review")
        check.assert_not_awaited()

    async def test_video_audio_review_defers_content_and_no_track_is_explicit(self):
        media = ValidatedMedia(b"control", "video.mp4", "video/mp4", "video", {"has_audio": True})
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=([(0.5, b"frame")], [{}]))), \
             patch("app.services.media_analysis.extract_video_audio", new=AsyncMock(return_value=b"track")), \
             patch("app.services.media_analysis.audio_layers", new=AsyncMock(return_value={"audio": {"transcription": ORIGINAL}})), \
             patch("app.services.media_analysis.check_content", new=AsyncMock()) as check:
            report = await analyze_media(media, review_first=True)
            self.assertEqual(report["content_analysis"]["analysis_status"], "pending_user_review")
            self.assertEqual(report["transcription"], ORIGINAL)
            media.details["has_audio"] = False
            silent = await analyze_media(media, review_first=True)
        check.assert_not_awaited()
        self.assertIn("Vídeo sem faixa de áudio: nenhuma fala foi transcrita ou checada.", silent["limitations"])
        self.assertNotIn("audio_analysis", silent)

    async def test_existing_default_flow_still_checks_ocr(self):
        media = ValidatedMedia(valid_png(), "controle.png", "image/png", "image", {})
        with patch("app.services.media_analysis.image_layers", new=AsyncMock(return_value={"ocr": {"text": ORIGINAL}})), \
             patch("app.services.media_analysis.check_content", new=AsyncMock(return_value={"veracity_status": "unverified"})) as check:
            await analyze_media(media)
        check.assert_awaited_once_with(ORIGINAL, "ocr", timeout=30)
