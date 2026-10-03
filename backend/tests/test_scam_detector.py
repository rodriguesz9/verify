import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core.pipeline import run_pipeline
from app.core.scam_detector import analyze_scam_indicators
from app.models.history import VerdictLabel


class ScamDetectorTests(unittest.TestCase):
    def test_evidence_contains_the_actual_matched_excerpt(self):
        text = "Atenção: Pague uma taxa para receber seu dinheiro."
        result = analyze_scam_indicators(text)
        self.assertIn(result["detected_patterns"][0]["matched_excerpt"], text)

    def test_unfamiliar_tld_alone_is_not_a_scam_verdict(self):
        self.assertFalse(analyze_scam_indicators("Um artigo de tecnologia", "https://example.site/article")["is_scam"])

    def test_tld_in_query_does_not_misclassify_official_domain(self):
        result = analyze_scam_indicators("Consulta de informação", "https://www.gov.br/search?q=.site")
        self.assertFalse(result["is_scam"])
        self.assertFalse(result["suspicious_url"])

    def test_official_name_in_unrelated_domain_does_not_bypass_the_check(self):
        self.assertTrue(analyze_scam_indicators("Consulta de informação", "https://correios-falso.com.br")["is_scam"])
        self.assertFalse(analyze_scam_indicators("Consulta de informação", "https://bbc.com/news")["is_scam"])

    def test_detects_values_owed_pix_fee_variant(self):
        result = analyze_scam_indicators(
            "URGENTE: Banco Central libera valores esquecidos no Pix. "
            "Pague uma taxa agora para receber."
        )

        self.assertTrue(result["is_scam"])
        self.assertGreater(result["scam_count"], 0)
        self.assertEqual(result["detected_patterns"][0]["category"], "Golpe do Pix / Dinheiro Fácil")

    def test_pipeline_marks_detected_fraud_as_scam_when_llm_falls_back(self):
        fallback_report = {
            "verdict": "Suspicious",
            "score": 50,
            "red_flags": [],
        }
        with (
            patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=[])),
            patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])),
            patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])),
            patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": 0})),
            patch("app.core.pipeline.generate_final_report", new=AsyncMock(return_value=fallback_report)),
        ):
            result = asyncio.run(
                run_pipeline("Pague uma taxa para receber valores esquecidos do Pix.")
            )

        self.assertEqual(result["report"]["verdict"], "Scam")
        self.assertEqual(result["report"]["score"], 15)

    def test_scam_is_a_persistable_verdict_label(self):
        self.assertEqual(VerdictLabel.SCAM.value, "Scam")
        self.assertEqual(VerdictLabel.SCAM.name, "SCAM")


if __name__ == "__main__":
    unittest.main()
