"""Fixed rejection diagnostics guide retrieval, never source votes or truth."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_research
from app.services.source_corroboration import document_selection_audit, select_comparison_documents


CLAIM = "A nave Aurora colidiu intencionalmente com o asteroide Zeta em 12 de agosto de 2021."
SHORT = "A nave Aurora colidiu com o asteroide Zeta em 12 de agosto de 2021."
COMPLETE = "Em 12 de agosto de 2021, a nave Aurora colidiu intencionalmente com o asteroide Zeta."
STAMP = "2026-10-21T12:00:00+00:00"


def doc(quote, url="https://www.bbc.com/public-control"):
    return {"url": url, "sentences": [quote], "sentence_roles": ["body"], "retrieved_at": STAMP,
            "source_role": "retrieved_reference", "title": "Control"}


class ReadingGapTests(unittest.TestCase):
    def test_missing_literal_qualifier_is_diagnostic_without_claim_or_body_disclosure(self):
        audit = document_selection_audit(CLAIM, [doc(SHORT)])
        gaps = audit["reading_gaps"]
        self.assertIn("not_exhaustive_not_evidence", gaps["scope"])
        self.assertEqual(gaps["claims"][0]["claim_id"], "c1")
        reasons = gaps["claims"][0]["reasons"]
        self.assertTrue(any("Intencionalidade" in row["reason"] for row in reasons))
        self.assertTrue(all(0 < row["rejected_candidate_count"] <= 20000 for row in reasons))
        encoded = json.dumps(audit, ensure_ascii=False)
        self.assertNotIn(CLAIM, encoded)
        self.assertNotIn(SHORT, encoded)
        self.assertEqual(audit["eligible_family_count"], 0)

    def test_diagnostics_and_repeated_calls_never_change_selection_or_input(self):
        docs = [doc(SHORT), doc(COMPLETE, "https://www.nasa.gov/public-control")]
        before = json.dumps(docs)
        selected = select_comparison_documents(CLAIM, docs)
        first = document_selection_audit(CLAIM, docs)
        second = document_selection_audit(CLAIM, docs)
        self.assertEqual(first, second)
        self.assertEqual(first["selected_source_urls"], [item["url"] for item in selected])
        self.assertEqual(json.dumps(docs), before)
        self.assertEqual(select_comparison_documents(CLAIM, docs), selected)
        self.assertEqual(first["eligible_family_count"], 1)

    def test_rejection_list_and_claim_ids_stay_bounded_and_do_not_contain_source_text(self):
        claims = " ".join(f"A pesquisadora Zeta recebeu o prêmio Delta em {year}." for year in range(2010,2017))
        docs = [doc("Registro sem sujeito, evento ou data alegados.", f"https://www.bbc.com/control-{i}") for i in range(20)]
        audit = document_selection_audit(claims, docs)
        self.assertLessEqual(len(audit["reading_gaps"]["claims"]), 5)
        self.assertTrue(all(len(row["reasons"]) <= 8 for row in audit["reading_gaps"]["claims"]))
        self.assertLessEqual(len(audit["excluded_sources"]), 10)
        self.assertNotIn(docs[0]["sentences"][0], json.dumps(audit))


class ResearchGapPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_receives_fixed_gaps_but_cannot_return_verdict_or_fabricated_proof(self):
        audit = document_selection_audit(CLAIM, [doc(SHORT)])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unit-test-not-secret", "SERPERAPI_KEY": "unit-test-not-secret",
                "OPENROUTER_API_KEY": "", "SOURCE_RESEARCH_ENABLED": "true"}, clear=True), \
             patch.object(source_research.gemini_client, "generate_text", new=AsyncMock(
                 return_value=json.dumps({"queries": [], "lead_ids": []}))) as model:
            result = await source_research.plan_source_research(CLAIM, [], [], audit)
        prompt = json.loads(model.await_args.args[0])
        self.assertEqual(prompt["original_claim"], CLAIM)
        self.assertEqual(prompt["selection_limits"]["reading_gaps"], audit["reading_gaps"])
        self.assertNotIn("verdict", result)
        self.assertEqual(result["queries"], [])
        model.assert_awaited_once()
