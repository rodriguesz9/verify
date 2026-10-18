"""Synthetic transport/policy controls, NOT a detector accuracy benchmark."""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
from helpers import valid_wav, valid_png
from app.services.claim_policy import text_report, publisher_family
from app.models.schemas import FactCheckResult
from app.models.history import VerdictLabel
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.pipeline import run_pipeline
from app.services.evidence_policy import media_report
from app.services.media_analysis import analyze_media
from app.services.media_validation import validate_media, ValidatedMedia
from app.services.speech_detector import detect_synthetic_speech

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)
CLAIM = "O município de Exemplo inaugurou a ponte em 2024"


def review(claim=CLAIM, rating="Verdadeiro", domain="aosfatos.org", **extra):
    return {"claim_text": claim, "rating": rating, "publisher": "Synthetic test publisher",
            "url": f"https://{domain}/synthetic-fixture-not-a-real-check", "review_date": "2026-09-01T12:00:00Z",
            "retrieval_provider": "google_fact_check", **extra}


def pair(claim=CLAIM, rating="Verdadeiro"):
    return [review(claim, rating), review(claim, rating, "boatos.org")]


class ClaimDecisionTests(unittest.TestCase):
    def test_distinct_reviews_support_or_refute(self):
        for rating, verdict, status in (("Verdadeiro", "Authentic", "supported"), ("Falso", "False", "refuted")):
            result = text_report(CLAIM, pair(rating=rating), now=NOW)
            self.assertEqual(result["verdict"], verdict)
            self.assertEqual(result["veracity_status"], status)
            self.assertIsNone(result["confidence"])
            self.assertIsNone(result["authenticity_percentage"])
        self.assertEqual(VerdictLabel.FALSE.value, "False")

    def test_different_proposition_never_matches(self):
        for text in (CLAIM.replace("inaugurou", "não inaugurou"), CLAIM.replace("2024", "2025"),
                     CLAIM.replace("Exemplo", "Outra Cidade"), CLAIM + " e cobrou R$ 500"):
            with self.subTest(text=text):
                self.assertEqual(text_report(text, pair(), now=NOW)["veracity_status"], "unverified")

    def test_normalization_does_not_erase_accents_or_numbers(self):
        for a, b in (("Minha avó recebeu R$ 10", "Meu avô recebeu R$ 10"),
                     ("O total foi 1.000", "O total foi 1,000"),
                     ("O total foi 10%", "O total foi 100%")):
            self.assertEqual(text_report(a, pair(b), now=NOW)["veracity_status"], "unverified")

    def test_only_whitespace_case_final_period_normalized(self):
        result = text_report("  " + CLAIM.upper() + ".  ", pair(), now=NOW)
        self.assertEqual(result["veracity_status"], "supported")

    def test_one_publisher_duplicate_or_related_sites_cannot_form_consensus(self):
        for evidence in ([review()], [review(), review(url="https://aosfatos.org/another")],
                         [review(domain="checamos.afp.com"), review(domain="factcheck.afp.com")]):
            self.assertEqual(text_report(CLAIM, evidence, now=NOW)["veracity_status"], "unverified")

    def test_any_corresponding_disagreement_blocks_verdict(self):
        result = text_report(CLAIM, [*pair(), review(rating="Falso", domain="fullfact.org")], now=NOW)
        self.assertEqual(result["veracity_status"], "conflicting")
        self.assertEqual(result["analysis_status"], "inconclusive")

    def test_ambiguous_rating_never_guessed(self):
        for rating in ("Não é falso", "mostly true", "Enganoso", "Falso ou verdadeiro", "N/D", "False: missing context"):
            with self.subTest(rating=rating):
                self.assertEqual(text_report(CLAIM, pair(rating=rating), now=NOW)["veracity_status"], "unverified")

    def test_question_quote_relative_time_fail_closed(self):
        for text in (CLAIM + "?", '"' + CLAIM + '"', CLAIM + " hoje", CLAIM + " ontem", CLAIM + " atualmente",
                     CLAIM + " semana passada", CLAIM + " neste mês", CLAIM + " recentemente", CLAIM + " today"):
            self.assertEqual(text_report(text, pair(text), now=NOW)["veracity_status"], "unverified")

    def test_missing_date_origin_or_unsafe_source_excluded(self):
        for field, value in (("review_date", None), ("review_date", "2027-01-01"), ("review_date", "bad-date"),
                             ("retrieval_provider", "llm"), ("url", "javascript:alert(1)"),
                             ("url", "https://aosfatos.org.evil.test/x"), ("url", "https://evil-aosfatos.org/x"),
                             ("url", "https://user:password@aosfatos.org/x")):
            with self.subTest(field=field, value=value):
                evidence = [{**item, field: value} for item in pair()]
                result = text_report(CLAIM, evidence, now=NOW)
                self.assertEqual(result["veracity_status"], "unverified")
                self.assertTrue(result["claim_assessments"][0]["excluded_evidence"])

    def test_unchecked_segment_prevents_whole_message_approval(self):
        result = text_report(CLAIM + ". Outra afirmação sem fonte.", pair(), now=NOW)
        self.assertEqual(result["veracity_status"], "unverified")
        self.assertEqual(result["claim_assessments"][0]["status"], "supported")

    def test_true_and_false_segments_are_mixed_not_all_false(self):
        other = "A ponte de Exemplo custou R$ 20 milhões"
        result = text_report(CLAIM + ". " + other, [*pair(), *pair(other, "Falso")], now=NOW)
        self.assertEqual(result["veracity_status"], "mixed")
        self.assertEqual(result["analysis_status"], "inconclusive")

    def test_more_than_five_segments_cannot_be_fully_verified(self):
        text = ". ".join([CLAIM] * 6)
        result = text_report(text, pair(), now=NOW)
        self.assertEqual(result["veracity_status"], "unverified")
        self.assertTrue(any("Limite" in item for item in result["limitations"]))

    def test_domain_substring_is_not_trusted(self):
        for domain in ("globo.com.evil.test", "reuters.fake.test", "not-bbc.com", "gov.br.evil.test"):
            self.assertNotEqual(check_domain_reputation("https://" + domain)["score"], 88)
            self.assertIsNone(publisher_family("https://" + domain))

    def test_media_origin_never_is_factual_truth(self):
        for data in ({}, {"sightengine": {"available": True, "genai_probability": 0}},
                     {"sightengine": {"available": True, "genai_probability": .99}, "hive": {"available": True, "ai_generated_score": .99}}):
            self.assertEqual(media_report(data)["veracity_status"], "unverified")


class EvidenceTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_returns_full_claim_and_review_date(self):
        claim = CLAIM + " " + "detalhes " * 70
        payload = {"claims": [{"text": claim, "claimDate": "2024-01-01T00:00:00Z", "claimReview": [
            {"textualRating": "Falso", "url": "https://aosfatos.org/test", "reviewDate": "2026-09-01T00:00:00Z",
             "publisher": {"name": "Aos Fatos", "site": "aosfatos.org"}}]}]}
        with patch.dict(os.environ, {"GOOGLE_FACT_CHECK_KEY": "test-only"}), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, json=payload))):
            result = await query_fact_check_api(claim)
        self.assertEqual(result[0].claim_text, claim)
        self.assertEqual(result[0].retrieval_provider, "google_fact_check")
        self.assertEqual(result.status, "success")

    async def test_google_error_no_results_and_no_key_distinguished(self):
        for status, payload, expected in ((403, {}, "error"), (429, {}, "error"), (200, {}, "no_results"), (200, [], "invalid_response")):
            with patch.dict(os.environ, {"GOOGLE_FACT_CHECK_KEY": "test-only"}), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(status, json=payload))):
                result = await query_fact_check_api(CLAIM)
                self.assertEqual(result.status, expected)
        with patch.dict(os.environ, {"GOOGLE_FACT_CHECK_KEY": ""}):
            self.assertEqual((await query_fact_check_api(CLAIM)).status, "not_configured")

    async def test_pipeline_cannot_approve_from_llm_or_related_news(self):
        with patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=["Invented paraphrase"])), \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[{"title": CLAIM, "link": "https://reuters.com/test"}])), \
             patch("app.core.pipeline.generate_final_report", new=AsyncMock(return_value={"verdict": "Authentic", "score": 100})) as model:
            result = await run_pipeline(CLAIM)
        self.assertEqual(result["report"]["veracity_status"], "unverified")
        self.assertEqual(result["report"]["claims"], [CLAIM])
        model.assert_not_awaited()

    async def test_pipeline_uses_retrieved_reviews_for_both_verdicts(self):
        for rating, verdict in (("Verdadeiro", "Authentic"), ("Falso", "False")):
            with patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[FactCheckResult(**r) for r in pair(rating=rating)])):
                result = await run_pipeline(CLAIM)
            self.assertEqual(result["report"]["verdict"], verdict)

    async def test_one_source_failure_does_not_abort_pipeline(self):
        with patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(side_effect=RuntimeError("private-detail"))), \
             patch("app.core.pipeline.search_news", new=AsyncMock(side_effect=RuntimeError("private-detail"))):
            result = await run_pipeline(CLAIM)
        self.assertEqual(result["report"]["analysis_status"], "inconclusive")
        self.assertNotIn("private-detail", str(result))

    async def test_audio_detector_is_opt_in_and_no_key_not_success(self):
        with patch.dict(os.environ, {"SIGHTENGINE_AUDIO_ENABLED": "false"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as request:
            self.assertEqual((await detect_synthetic_speech(valid_wav()))["status"], "disabled")
            request.assert_not_awaited()

    async def test_audio_uses_actual_bytes_and_documented_score(self):
        response = httpx.Response(200, json={"status": "success", "type": {"ai_speech": .98}})
        with patch.dict(os.environ, {"SIGHTENGINE_AUDIO_ENABLED": "true", "SIGHTENGINE_API_USER": "test", "SIGHTENGINE_API_SECRET": "test"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as request:
            result = await detect_synthetic_speech(valid_wav())
        self.assertEqual(result["ai_speech_score"], .98)
        self.assertEqual(request.call_args.kwargs["files"]["audio"][1], valid_wav())
        self.assertEqual(request.call_args.kwargs["data"]["models"], "ai_speech")
        self.assertNotIn("params", request.call_args.kwargs)

    async def test_audio_access_errors_and_invalid_scores_fail_closed(self):
        for status, value in ((403, .99), (429, .99), (200, True), (200, 4), (200, "0.99")):
            with patch.dict(os.environ, {"SIGHTENGINE_AUDIO_ENABLED": "true", "SIGHTENGINE_API_USER": "test", "SIGHTENGINE_API_SECRET": "test"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(status, json={"status": "success", "type": {"ai_speech": value}}))):
                self.assertFalse((await detect_synthetic_speech(valid_wav()))["available"])

    async def test_audio_consensus_uses_acoustics_not_transcript(self):
        media = await validate_media(valid_wav(), "fake.wav", "audio/wav")
        # Consensus policy control; silence admission has separate real-byte tests.
        with patch("app.services.media_analysis.detect_synthetic_speech", new=AsyncMock(return_value={"available": True, "status": "success", "ai_speech_score": .98})), \
             patch("app.services.media_analysis.prepare_speech_input", new=AsyncMock(return_value=(b"speech-control", False, "success"))), \
             patch("app.services.media_analysis.check_hive_media", new=AsyncMock(return_value={"available": True, "status": "success", "ai_generated_score": .97})):
            report = await analyze_media(media)
        self.assertEqual(report["verdict"], "AI_Generated")
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["authenticity_status"], "ai_indications")

    async def test_audio_disagreement_or_low_scores_not_human_certificate(self):
        for a, b in ((.99, .01), (.01, .02)):
            report = media_report({"sightengine_audio": {"available": True, "ai_speech_score": a},
                                   "hive": {"available": True, "ai_generated_score": b}}, "audio")
            self.assertEqual(report["analysis_status"], "inconclusive")
            self.assertNotEqual(report["verdict"], "Authentic")

    async def test_ocr_and_transcription_get_separate_content_report(self):
        media = await validate_media(valid_png())
        with patch("app.services.media_analysis.image_layers", new=AsyncMock(return_value={"ocr": {"text": CLAIM}})), \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[FactCheckResult(**r) for r in pair()])):
            report = await analyze_media(media)
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["content_analysis"]["veracity_status"], "supported")
        self.assertEqual(report["content_analysis"]["origin"], "ocr")
