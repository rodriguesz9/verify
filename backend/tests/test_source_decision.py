"""Offline combination controls; invented sources are not accuracy benchmarks."""
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

from helpers import app
from app.core.pipeline import run_pipeline
from app.services.claim_policy import text_report
from app.services.source_decision import apply_source_decision, SOURCE_SCORE_SEMANTICS
from app.api.history import _display_score
from types import SimpleNamespace

CLAIM = "Elizabeth II morreu em 8 de setembro de 2022."


def layer(text=CLAIM, status="corroborated", families=("royal", "bbc")):
    relation = "supports" if status == "corroborated" else "refutes"
    return {"version": "source_corroboration_v1", "status": "success", "state": status,
        "decision_role": "grounded_source_comparison", "coverage": {"complete_claim_coverage": True},
        "claims": [{"claim_id": "c1", "claim": text, "status": status,
            "explanation": "Controle simulado, não leitura de fonte real.", "evidence": [
                {"source_id": f"s{i}", "url": f"https://{family}.example.test/article", "publisher_family": family,
                 "source_role": "retrieved_reference", "excerpt": text, "relation": relation,
                 "retrieved_at": "2026-10-13T12:00:00+00:00"} for i, family in enumerate(families, 1)]}]}


class SourceDecisionTests(unittest.TestCase):
    def test_original_institutional_record_is_labelled_as_one_primary_source(self):
        text = "O IBGE informou que o PIB brasileiro cresceu 4,2% em 2020."
        comparison = layer(text, families=("ibge",))
        comparison["claims"][0]["evidence"][0].update(url="https://agenciadenoticias.ibge.gov.br/release", source_type="primary")
        result = apply_source_decision(text, text_report(text, []), comparison)
        self.assertEqual(result["veracity_status"], "supported")
        self.assertTrue(result["original_record_only"])
        self.assertIn("não duas fontes independentes", result["summary"])
        self.assertIsNone(result["confidence"])
        for change in ({"url":"https://www.bbc.com/story", "publisher_family":"bbc"},
                       {"source_type":"editorial"}, {"source_role":"submitted_source"}):
            comparison["claims"][0]["evidence"][0].update(change)
            self.assertEqual(apply_source_decision(text, text_report(text, []), comparison)["veracity_status"], "unverified")

    def test_source_confirmation_changes_fact_decision_without_inventing_probability(self):
        original = text_report(CLAIM, [])
        result = apply_source_decision(CLAIM, original, layer())
        self.assertEqual(result["veracity_status"], "supported")
        self.assertEqual(result["veracity_decision_basis"], "retrieved_sources")
        self.assertEqual(result["score_semantics"], SOURCE_SCORE_SEMANTICS)
        self.assertIsNone(result["confidence"])
        self.assertTrue(result["veracity_decision_coverage_complete"])
        self.assertEqual(original["veracity_status"], "unverified")
        self.assertNotIn("veracity_decision_basis", original)

    def test_public_source_decision_uses_plain_true_false_words_and_preserves_scope(self):
        for state, label in (("corroborated", "verdadeira"), ("refuted", "falsa")):
            with self.subTest(state=state):
                result = apply_source_decision(CLAIM, text_report(CLAIM, []), layer(status=state))
                self.assertIn("verificada como " + label, result["summary"])
                self.assertIn("fontes independentes consultadas", result["summary"])
                self.assertIn("a análise pode errar", result["summary"])
                self.assertNotRegex(result["summary"], r"(?i)corrobor|refutad|refutação")
                self.assertEqual(result["claim_assessments"][0]["evidence"][0]["excerpt"], CLAIM)

    def test_two_refutations_are_attributed_not_authenticity_claims(self):
        result = apply_source_decision(CLAIM, text_report(CLAIM, []), layer(status="refuted"))
        self.assertEqual(result["verdict"], "False")
        self.assertEqual(result["authenticity_status"], "not_applicable")
        self.assertIn("fontes", result["summary"])
        self.assertIsNone(_display_score(SimpleNamespace(raw_result=result, verdict_score=0)))

    def test_existing_decisive_reviews_and_scam_are_not_overwritten(self):
        for change in ({"veracity_status": "supported", "verdict": "Authentic"},
                       {"veracity_status": "refuted", "verdict": "False"},
                       {"veracity_status": "mixed"}, {"veracity_status": "conflicting"}, {"verdict": "Scam"}):
            original = {**text_report(CLAIM, []), **change}
            self.assertEqual(apply_source_decision(CLAIM, original, layer()), original)

    def test_unsupported_partial_or_invented_statement_does_not_approve_original(self):
        original = text_report(CLAIM, [])
        for changed in (layer(families=("bbc",)), layer(families=("bbc", "bbc")),
                        layer(text=CLAIM.replace("2022", "2023")), {**layer(), "status": "invalid_response"},
                        {**layer(), "version": "unknown"}, {**layer(), "decision_role": "context_only"}):
            self.assertEqual(apply_source_decision(CLAIM, original, changed), original)
        submitted = layer()
        submitted["claims"][0]["evidence"][0]["source_role"] = "submitted_source"
        self.assertEqual(apply_source_decision(CLAIM, original, submitted), original)

    def test_uncovered_sentence_blocks_global_confirmation(self):
        text = CLAIM + " Outra informação sem confirmação."
        result = apply_source_decision(text, text_report(text, []), layer())
        self.assertEqual(result["veracity_status"], "unverified")
        self.assertEqual(result["analysis_status"], "inconclusive")
        self.assertFalse(result["veracity_decision_coverage_complete"])
        self.assertEqual(result["claim_assessments"][0]["status"], "supported")
        self.assertEqual(result["claim_assessments"][1]["status"], "unverified")

    def test_complete_mixed_reviews_and_sources_keep_both_evidence_modes(self):
        text = CLAIM + " Outra afirmação documental."
        original = text_report(text, [])
        original["claim_assessments"][1].update(status="refuted", evidence=[{"publisher": "Controle"}])
        result = apply_source_decision(text, original, layer())
        self.assertEqual(result["veracity_status"], "mixed")
        self.assertEqual(result["veracity_decision_basis"], "mixed_evidence")
        self.assertEqual(result["claim_assessments"][1], original["claim_assessments"][1])

    def test_excess_segments_or_duplicate_claim_id_abstain(self):
        text = " ".join([CLAIM] * 6)
        original = text_report(text, [])
        self.assertEqual(apply_source_decision(text, original, layer()), original)
        repeated = layer()
        repeated["claims"] *= 2
        self.assertEqual(apply_source_decision(CLAIM, text_report(CLAIM, []), repeated), text_report(CLAIM, []))

    def test_long_article_keeps_partial_evidence_without_approving_unread_remainder(self):
        text = CLAIM + " " + " ".join(f"Informação adicional {i} sem confirmação." for i in range(1, 6))
        result = apply_source_decision(text, text_report(text, []), layer())
        self.assertEqual(result["claim_assessments"][0]["status"], "supported")
        self.assertEqual(len(result["claim_assessments"]), 5)
        self.assertEqual(result["veracity_status"], "unverified")
        self.assertFalse(result["veracity_decision_coverage_complete"])

    def test_five_supported_parts_cannot_approve_sixth_unread_part(self):
        parts = [f"O documento Alfa registrou o evento {i}." for i in range(6)]
        text = " ".join(parts)
        comparison = layer(parts[0])
        comparison["claims"] = [layer(part)["claims"][0] for part in parts[:5]]
        result = apply_source_decision(text, text_report(text, []), comparison)
        self.assertTrue(all(item["status"] == "supported" for item in result["claim_assessments"]))
        self.assertEqual(result["veracity_status"], "unverified")
        self.assertFalse(result["veracity_decision_coverage_complete"])


class SourcePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, comparison):
        attribution = {"status": "no_results", "decision_role": "source_attribution_only", "matches": [],
            "coverage": {}, "limitations": [], "_documents": [{"sentences": ["INTERNAL PAGE BODY"], "url": "https://www.royal.uk/control"}]}
        before = deepcopy(attribution)
        with (patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})),
              patch("app.core.pipeline._retrieve_source_attribution", new=AsyncMock(return_value=attribution)),
              patch("app.core.pipeline.corroborate_sources", new=AsyncMock(side_effect=comparison if isinstance(comparison, Exception) else None,
                  return_value=comparison)) as compare):
            result = await run_pipeline(CLAIM)
        self.assertEqual(attribution, before)
        return result["report"], compare

    async def test_page_bodies_removed_before_return_and_comparison_can_decide_without_fact_check(self):
        report, comparison = await self.run_control(layer())
        self.assertEqual(report["veracity_status"], "supported")
        self.assertNotIn("_documents", report["source_attribution"])
        self.assertNotIn("INTERNAL PAGE BODY", str(report))
        self.assertEqual(comparison.await_args.args[1][0]["sentences"], ["INTERNAL PAGE BODY"])

    async def test_comparison_failure_keeps_original_evidence_and_no_private_exception(self):
        report, _ = await self.run_control(RuntimeError("private-secret-text"))
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertNotIn("private-secret-text", str(report))
        self.assertEqual(report["source_corroboration"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
