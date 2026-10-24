"""Release guards for Juan's adapted opt-in. All provider replies are simulated."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from helpers import app, FakeSession, override_auth_and_db
from app.core.pipeline import run_pipeline
from app.core.gemini_analyzer import ClaimsExtraction
from app.models.schemas import FactCheckResult
from app.services.claim_policy import text_report
from app.services.pdf_snapshot import attach_pdf_snapshot, verify_pdf_snapshot
from test_claim_decisions import pair
from test_source_decision import CLAIM, layer


class DetailedPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, comparison=None, reviews=None, hints=None, detailed=True):
        attribution = {"status": "no_results", "matches": [], "coverage": {},
                       "limitations": [], "_documents": []}
        with ExitStack() as stack:
            stack.enter_context(patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(
                return_value=hints if hints is not None else [])))
            stack.enter_context(patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=reviews or [])))
            stack.enter_context(patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[
                {"title": CLAIM, "link": "https://example.test/context", "snippet": "UNVALIDATED NEWS SNIPPET"}])))
            stack.enter_context(patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})))
            stack.enter_context(patch("app.core.pipeline._retrieve_source_attribution", new=AsyncMock(return_value=attribution)))
            compare = stack.enter_context(patch("app.core.pipeline.corroborate_sources", new=AsyncMock(
                side_effect=comparison if isinstance(comparison, Exception) else None,
                return_value=comparison or {"version": "source_corroboration_v1", "status": "no_results",
                    "state": "insufficient", "claims": [], "coverage": {}, "decision_role": "grounded_source_comparison"})))
            legacy = stack.enter_context(patch("app.core.pipeline.generate_final_report", new=AsyncMock(
                side_effect=AssertionError("Legacy classifier must never run"))))
            result = await run_pipeline(CLAIM, use_detailed_report=detailed)
        legacy.assert_not_awaited()
        return result["report"], compare

    async def test_context_and_model_opinion_cannot_become_evidence_in_detailed_mode(self):
        report, compare = await self.run_control()
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["provider_coverage"]["serper"]["decision_role"], "context_only")
        self.assertNotIn("UNVALIDATED NEWS SNIPPET", report["plain_explanation"])
        self.assertNotIn("example.test/context", str(report["report_explanation"]))
        compare.assert_awaited_once()

    async def test_grounded_support_and_refutation_survive_detailed_mode_unchanged(self):
        for state, verdict in (("corroborated", "Authentic"), ("refuted", "False")):
            baseline, _ = await self.run_control(layer(status=state), detailed=False)
            detailed, comparison = await self.run_control(layer(status=state))
            self.assertEqual(detailed["verdict"], verdict)
            # Separate executions need not take identical wall-clock time;
            # every factual/coverage field besides measured duration agrees.
            for report in (baseline, detailed):
                elapsed = report["provider_coverage"]["analysis_budget"].pop("elapsed_seconds")
                self.assertGreaterEqual(elapsed, 0)
                self.assertLessEqual(elapsed, 420)
            self.assertEqual({k: v for k, v in detailed.items() if k not in {"plain_explanation", "report_explanation"}},
                             {k: v for k, v in baseline.items() if k != "plain_explanation"})
            self.assertEqual(detailed["report_explanation"]["decision_role"], "explanation_only")
            comparison.assert_awaited_once()

    async def test_comparison_failure_never_discards_contract_or_discloses_error(self):
        report, compare = await self.run_control(RuntimeError("PRIVATE-KEY-AND-ERROR"))
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertIn("policy_version", report)
        self.assertIn("claim_assessments", report)
        self.assertNotIn("PRIVATE-KEY-AND-ERROR", str(report))
        compare.assert_awaited_once()

    async def test_editorial_evidence_is_preserved_when_gemini_extraction_has_no_quota(self):
        # Multiple sentences exercise extraction; reviews cover the exact whole
        # input, preserving both the editorial decision and the quota failure.
        from test_claim_decisions import CLAIM as EDITORIAL_CLAIM
        text = EDITORIAL_CLAIM + ". A obra não recebeu recursos adicionais em 2025."
        with patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=ClaimsExtraction(status="rate_limited"))) as extraction, \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[FactCheckResult(**r) for r in pair(claim=text)])), \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])), \
             patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={})), \
             patch("app.core.pipeline._retrieve_source_attribution", new=AsyncMock(return_value={"status": "no_results", "matches": [], "coverage": {}})), \
             patch("app.core.pipeline.corroborate_sources", new=AsyncMock()) as cross, \
             patch("app.core.pipeline.generate_final_report", new=AsyncMock(side_effect=TimeoutError())) as legacy:
            report = (await run_pipeline(text, use_detailed_report=True))["report"]
        extraction.assert_awaited_once_with(text)
        self.assertEqual(report["claims"], [text])
        self.assertEqual(report["verdict"], "Authentic")
        self.assertEqual(report["veracity_status"], "supported")
        self.assertEqual(report["provider_coverage"]["gemini"]["status"], "rate_limited")
        cross.assert_not_awaited()
        legacy.assert_not_awaited()

    async def test_detailed_report_remains_exportable_without_reanalysis(self):
        report, _ = await self.run_control(layer())
        report.update(content_type="text", query_input=CLAIM, analyzed_at=datetime.now(timezone.utc).isoformat())
        signed = attach_pdf_snapshot(report)
        self.assertEqual(signed["pdf_export_status"], "ready")
        self.assertEqual(verify_pdf_snapshot(signed["pdf_snapshot_token"], None), report)


class DetailedRouteOptInTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()
        override_auth_and_db(None, self.db)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def test_text_batch_and_link_request_explanations_without_changing_pipeline_data(self):
        original = text_report(CLAIM, [])
        before = deepcopy(original)
        result = {"report": original, "metrics": {"text_ai_probability": None, "earliest_known_date": None}}
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value=result)) as text, \
             patch("app.api.check_url.run_pipeline", new=AsyncMock(return_value=result)) as url, \
             patch("app.api.check_text.verify_limit", new=AsyncMock()), \
             patch("app.api.check_url.verify_limit", new=AsyncMock()), \
             patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value={
                 "text": CLAIM + " Este é um controle simulado de link.", "final_url": "https://example.test/final"})):
            self.assertEqual(self.client.post("/api/check-text", json={"text": CLAIM}).status_code, 200)
            self.assertEqual(self.client.post("/api/check-text-batch", json={"texts": [CLAIM, CLAIM]}).status_code, 200)
            self.assertEqual(self.client.post("/api/check-url", json={"url": "https://example.test/article"}).status_code, 200)
        self.assertEqual(text.await_count, 3)
        self.assertTrue(all(call.kwargs.get("use_detailed_report") is True for call in text.await_args_list))
        self.assertTrue(url.await_args.kwargs["use_detailed_report"])
        self.assertEqual(original, before)


if __name__ == "__main__":
    unittest.main()
