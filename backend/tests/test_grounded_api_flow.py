"""Offline API -> real pipeline -> literal source guards -> stored report.

Retrieval and the provider's passage-ID selection are test doubles. The final
decision, explanation, persistence and signed snapshot are production code.
These synthetic controls are functional tests, never live accuracy samples.
"""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import FakeSession, app, fake_user, override_auth_and_db
from app.core.openrouter_service import GeneratedText
from app.models.history import Verification
from app.services.competition_relations import competition_outcome_relation
from app.services.launch_relations import launch_date_relation
from app.services.pdf_snapshot import verify_pdf_snapshot


def document(url, sentence):
    return {"url": url, "sentences": [sentence], "sentence_roles": ["body"],
            "title": "Synthetic functional control", "truncated": False,
            "retrieved_at": "2026-10-17T12:00:00+00:00"}


class GroundedApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user, self.db = fake_user(), FakeSession()
        override_auth_and_db(self.user, self.db)

    def tearDown(self):
        app.dependency_overrides.clear()

    def check(self, claim, documents, helper):
        async def ids_only(prompt, **_kwargs):
            payload = json.loads(prompt)
            evidence = []
            for source in payload["sources"]:
                for passage in source["passages"]:
                    relation = helper(claim, passage["quote"])
                    if relation:
                        evidence.append({"source_id": source["source_id"],
                                         "excerpt_id": passage["excerpt_id"], "relation": relation})
                        break
            return GeneratedText(json.dumps({"claims": [{"claim_id": "c1", "evidence": evidence}]}))

        attribution = {"status": "found", "decision_role": "source_attribution_only",
                       "matches": [], "coverage": {}, "limitations": [], "_documents": documents}
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter"}),
              patch("app.api.check_text.verify_limit", new=AsyncMock()),
              patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])),
              patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None})),
              patch("app.core.pipeline._retrieve_source_attribution", new=AsyncMock(return_value=attribution)),
              patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=ids_only))):
            response = self.client.post("/api/check-text", json={"text": claim})
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertNotIn("_documents", report["source_attribution"])
        self.assertEqual(report["query_input"], claim)
        self.assertEqual(report["content_type"], "text")
        self.assertEqual(report["pdf_export_status"], "ready")
        stored = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verify_pdf_snapshot(report["pdf_snapshot_token"], self.user), stored.raw_result)
        self.assertEqual(self.db.commits, 1)
        return report

    def test_launch_support_reaches_explanation_storage_and_snapshot(self):
        claim = "A missão Aurora IV foi lançada em 16 de novembro de 2001."
        docs = [document("https://www.nasa.gov/control", "The Aurora IV mission was launched on November 16, 2001."),
                document("https://www.bbc.com/control", claim)]
        report = self.check(claim, docs, launch_date_relation)
        self.assertEqual(report["veracity_status"], "supported")
        self.assertEqual(len(report["source_corroboration"]["claims"][0]["evidence"]), 2)
        self.assertIn("mesma missão", str(report))

    def test_title_refutation_keeps_literal_quotes_in_exportable_report(self):
        claim = "O Brasil venceu a Copa do Mundo de futebol masculino de 2014."
        first = "A Copa do Mundo de futebol masculino de 2014 foi vencida pela Alemanha."
        second = "Germany won the 2014 FIFA World Cup."
        report = self.check(claim, [document("https://www.cnnbrasil.com.br/control", first),
            document("https://www.bbc.com/control", second)], competition_outcome_relation)
        self.assertEqual(report["veracity_status"], "refuted")
        self.assertEqual({item["excerpt"] for item in report["source_corroboration"]["claims"][0]["evidence"]}, {first, second})

    def test_one_family_cannot_turn_successful_http_into_factual_confirmation(self):
        claim = "A missão Aurora IV foi lançada em 16 de novembro de 2001."
        report = self.check(claim, [document("https://www.nasa.gov/control", claim)], launch_date_relation)
        self.assertEqual(report["veracity_status"], "unverified")


if __name__ == "__main__":
    unittest.main()
