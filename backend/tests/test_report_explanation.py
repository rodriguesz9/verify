"""Pure explanation guards; no live provider claims or accuracy measurements."""
from copy import deepcopy
import unittest
from app.services.claim_policy import text_report
from app.services.report_explanation import enrich_grounded_report
from test_claim_decisions import CLAIM, pair


class ReportExplanationTests(unittest.TestCase):
    def test_only_explanation_fields_change_and_original_is_not_mutated(self):
        original = text_report(CLAIM, [])
        before = deepcopy(original)
        result = enrich_grounded_report(original)
        self.assertEqual(original, before)
        self.assertEqual({k: v for k, v in result.items() if k not in {"plain_explanation", "report_explanation"}},
                         {k: v for k, v in original.items() if k != "plain_explanation"})
        self.assertEqual(enrich_grounded_report(result), result)
        result["claim_assessments"][0]["status"] = "refuted"
        self.assertEqual(original["claim_assessments"][0]["status"], "unverified")

    def test_literal_negation_dates_and_quotes_are_never_shortened(self):
        claim = "Elizabeth II não morreu em 9 de setembro de 2022."
        original = text_report(claim, [])
        item = original["claim_assessments"][0]
        item["evidence_mode"] = "retrieved_sources"
        item["evidence"] = [{"url": "https://example.test/article", "claim_text": claim,
                             "excerpt": claim, "relation": "supported"}]
        result = enrich_grounded_report(original)
        self.assertIn(claim, result["plain_explanation"])
        self.assertIn(claim, result["report_explanation"]["claims"][0]["references"][0]["excerpt"])

    def test_excluded_context_and_private_provider_errors_are_not_explanations(self):
        report = text_report(CLAIM, [])
        report["claim_assessments"][0]["excluded_evidence"] = [{"url": "https://excluded.example/secret", "excerpt": "EXCLUDED"}]
        report["serper_news"] = [{"title": "Invented true verdict", "snippet": "PRIVATE-SNIPPET"}]
        report["provider_coverage"] = {"model": {"status": "timeout", "reason": "PRIVATE-KEY", "error": "PRIVATE-ERROR"}}
        result = enrich_grounded_report(report)
        self.assertIn("tempo disponível", result["plain_explanation"])
        for secret in ("EXCLUDED", "PRIVATE-SNIPPET", "PRIVATE-KEY", "PRIVATE-ERROR", "excluded.example"):
            self.assertNotIn(secret, result["plain_explanation"])
            self.assertNotIn(secret, str(result["report_explanation"]))

    def test_refutation_uses_existing_decision_not_synthetic_media_guess(self):
        report = text_report(CLAIM, pair(CLAIM, "Falso"))
        result = enrich_grounded_report(report)
        self.assertEqual(result["verdict"], "False")
        self.assertIn("refutado", result["plain_explanation"])
        self.assertEqual(result["authenticity_status"], "not_applicable")

    def test_unsafe_or_excluded_accepted_rows_are_not_rendered(self):
        report = text_report(CLAIM, [])
        report["claim_assessments"][0]["evidence"] = [
            {"url": url, "relation": "supported", "excerpt": "DO NOT RENDER"}
            for url in ("javascript:alert(1)", "https://user:password@example.test", "http://example.test", "https://example.test:444/path")]
        report["claim_assessments"][0]["evidence"].append({"url": "https://example.test/excluded", "relation": "supported", "exclusion_reason": "excluded"})
        self.assertEqual(enrich_grounded_report(report)["report_explanation"]["claims"][0]["references"], [])

    def test_reviewed_claim_is_not_presented_as_article_quote_and_large_quote_not_cut(self):
        report = text_report(CLAIM, [])
        item = report["claim_assessments"][0]
        item["evidence"] = [{"url": "https://example.test/review", "relation": "supported", "claim_text": CLAIM, "excerpt": CLAIM}]
        result = enrich_grounded_report(report)
        self.assertNotIn("Trecho citado pela análise", result["plain_explanation"])
        item["evidence_mode"] = "retrieved_sources"
        item["evidence"][0]["excerpt"] = "não " + "x" * 700
        self.assertNotIn("excerpt", enrich_grounded_report(report)["report_explanation"]["claims"][0]["references"][0])

    def test_scam_warning_and_mixed_decision_are_preserved(self):
        report = text_report(CLAIM, [], {"is_scam": True, "detected_patterns": []})
        result = enrich_grounded_report(report)
        self.assertTrue(result["plain_explanation"].startswith(report["plain_explanation"]))
        self.assertEqual(result["verdict"], "Scam")
        mixed = {**text_report(CLAIM, []), "veracity_status": "mixed"}
        self.assertEqual(enrich_grounded_report(mixed)["veracity_status"], "mixed")

    def test_bounded_output_and_unknown_contract_remain_conservative(self):
        report = text_report(CLAIM, [])
        report["claim_assessments"] *= 20
        self.assertEqual(len(enrich_grounded_report(report)["report_explanation"]["claims"]), 5)
        for malformed in (None, {}, {"veracity_status": "unknown"}, {"veracity_status": "supported", "plain_explanation": None}):
            self.assertEqual(enrich_grounded_report(malformed), malformed)


if __name__ == "__main__":
    unittest.main()
