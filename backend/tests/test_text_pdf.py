"""Offline export controls. Fictitious sources do not validate real accuracy."""
import copy
import shutil
import subprocess
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from helpers import app, fake_user, FakeSession, override_auth_and_db
from app.services.claim_policy import text_report
from app.services.pdf_snapshot import attach_pdf_snapshot, verify_pdf_snapshot
from app.services.extracted_text_review import attach_text_review
from test_extracted_text_review import source_report, ORIGINAL

TEXT = "Controle fictício: não pague R$ 123,45 em 04/10/2026."


def original_text_report(**overrides):
    return {**text_report(TEXT, []), "content_type": "text", "query_input": TEXT,
            "analyzed_at": "2026-10-04T10:00:00+00:00", **overrides}


class TextPdfTests(unittest.TestCase):
    def setUp(self):
        self.user = fake_user(); self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)
        self.addCleanup(self.client.close); self.addCleanup(app.dependency_overrides.clear)

    def export(self, report):
        token = attach_pdf_snapshot(report, self.user)["pdf_snapshot_token"]
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(side_effect=AssertionError("Reanalysis"))) as pipeline, \
             patch("app.api.check_url.fetch_page_text", new=AsyncMock(side_effect=AssertionError("Refetch"))) as fetch, \
             patch("app.api.verificacao.verify_limit", new=AsyncMock(side_effect=AssertionError("Quota"))) as quota:
            response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        pipeline.assert_not_awaited(); fetch.assert_not_awaited(); quota.assert_not_awaited()
        self.assertTrue(response.content.startswith(b"%PDF"))
        return response

    def extract(self, response):
        return subprocess.run(["pdftotext", "-", "-"], input=response.content,
                              capture_output=True, check=True).stdout.decode()

    def test_new_text_check_signed_after_persistence_without_mutating_pipeline(self):
        original = text_report(TEXT, []); before = copy.deepcopy(original)
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value={"report": original, "metrics": {"text_ai_probability": None}})), \
             patch("app.api.check_text.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-text", json={"text": TEXT})
        self.assertEqual(response.status_code, 200)
        returned = response.json(); stored = self.db.added[0].raw_result
        self.assertEqual(returned["pdf_export_status"], "ready")
        self.assertEqual(verify_pdf_snapshot(returned["pdf_snapshot_token"], self.user), stored)
        self.assertEqual(original, before)
        self.assertNotIn("pdf_snapshot_token", stored)
        self.assertEqual(self.db.commits, 1)
        self.export(stored)
        self.assertEqual(self.db.commits, 1)

    def test_link_preserves_final_url_page_text_and_static_limits(self):
        pipeline_report = text_report(TEXT, [])
        scraped = {"text": TEXT + " Este texto é apenas um controle de teste.",
                   "final_url": "https://example.test/final", "extraction_details":
                   {"method": "static_html", "truncated": True, "rendered_browser": False}}
        with patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value=scraped)), \
             patch("app.api.check_url.run_pipeline", new=AsyncMock(return_value={"report": pipeline_report,
                   "metrics": {"text_ai_probability": None, "earliest_known_date": None}})), \
             patch("app.api.check_url.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-url", json={"url": "https://example.test/original"})
        self.assertEqual(response.status_code, 200)
        report = verify_pdf_snapshot(response.json()["pdf_snapshot_token"], self.user)
        self.assertEqual(report["source_text"], scraped["text"])
        self.assertEqual(report["source_url"], scraped["final_url"])
        self.assertEqual(report["query_input"], "https://example.test/original")
        self.assertNotIn("source_text", pipeline_report)
        self.assertNotIn("pdf_snapshot_token", self.db.added[0].raw_result)
        self.export(report)

    def test_batch_successes_export_errors_do_not_and_no_tokens_persist(self):
        success = {"report": text_report(TEXT, []), "metrics": {"text_ai_probability": None}}
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(side_effect=[success, RuntimeError("offline control")])), \
             patch("app.api.check_text.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-text-batch", json={"texts": [TEXT, TEXT + " Erro simulado."]})
        self.assertEqual(response.status_code, 200)
        good, bad = response.json()["results"]
        self.assertEqual(good["pdf_export_status"], "ready")
        self.assertEqual(bad["pdf_export_status"], "unavailable")
        self.assertEqual(verify_pdf_snapshot(good["pdf_snapshot_token"], self.user), self.db.added[0].raw_result)
        self.assertNotIn("pdf_snapshot_token", self.db.added[0].raw_result)
        self.assertEqual(self.db.commits, 1)

    def test_text_signatures_expiry_ownership_tampering_and_legacy_fail_closed(self):
        report = original_text_report(); token = attach_pdf_snapshot(report, self.user, now=1000)["pdf_snapshot_token"]
        self.assertEqual(verify_pdf_snapshot(token, self.user, now=1001), report)
        for candidate, user, now, expected in ((token, fake_user(), 1001, 403), (token, None, 1001, 403),
                                              (token, self.user, 4600, 410), (token[:-1] + "x", self.user, 1001, 422)):
            with self.assertRaises(HTTPException) as caught:
                verify_pdf_snapshot(candidate, user, now=now)
            self.assertEqual(caught.exception.status_code, expected)
        for change in ({"analyzed_at": None}, {"analyzed_at": "2026-10-04"}, {"query_input": ""},
                       {"claim_assessments": None}, {"policy_version": None}, {"error": True},
                       {"content_type": "url"}, {"content_type": []}, {"veracity_status": []}):
            self.assertEqual(attach_pdf_snapshot({**report, **change})["pdf_export_status"], "unavailable")
        fresh = attach_pdf_snapshot(attach_pdf_snapshot(report, self.user, now=1000), self.user, now=5000)
        self.assertEqual(verify_pdf_snapshot(fresh["pdf_snapshot_token"], self.user, now=5001), report)

    def test_export_snapshot_does_not_embed_review_capability(self):
        report = original_text_report(text_review_token="vrev1.secret")
        restored = verify_pdf_snapshot(attach_pdf_snapshot(report)["pdf_snapshot_token"])
        self.assertNotIn("text_review_token", restored)
        self.assertEqual(report["text_review_token"], "vrev1.secret")

    def test_anonymous_text_exports_without_storage_and_review_token_is_not_pdf(self):
        override_auth_and_db(None, self.db)
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value={
            "report": text_report(TEXT, []), "metrics": {"text_ai_probability": None}})), \
             patch("app.api.check_text.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-text", json={"text": TEXT})
        self.assertEqual(response.status_code, 200)
        pdf = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": response.json()["pdf_snapshot_token"]})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(self.db.added, []); self.assertEqual(self.db.commits, 0)
        wrong_purpose = attach_text_review(source_report())["text_review_token"]
        rejected = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": wrong_purpose})
        self.assertEqual(rejected.status_code, 422)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required")
    def test_veracity_states_and_corresponding_excluded_sources_are_faithful(self):
        for state, label in (("supported", "Corroborado"), ("refuted", "Refutado"),
                             ("conflicting", "Fontes discordantes"), ("unverified", "Evidência insuficiente")):
            with self.subTest(state=state):
                report = original_text_report(veracity_status=state, claim_assessments=[
                    {"claim": TEXT, "status": state, "explanation": "Controle fictício de apresentação, não valida precisão.",
                     "evidence": [{"publisher": "Fonte fictícia", "url": "https://example.test/checagem", "rating": "Controle", "review_date": "2026-10-01"}],
                     "excluded_evidence": [{"publisher": "Fonte excluída", "url": "https://example.test/excluida", "exclusion_reason": "Afirmação diferente"}]}])
                text = self.extract(self.export(report))
                for value in (label, TEXT, "Fonte fictícia", "Fonte excluída", "Afirmação diferente", "Precisão não calibrada", report["analyzed_at"]):
                    self.assertIn(value, text)
                for forbidden in ("vpdf1", "vrev1", "ORIGEM DA MÍDIA", "EXIFTool", "Hive / Sightengine", "VER-"):
                    self.assertNotIn(forbidden, text)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required")
    def test_human_review_pdf_retains_both_texts_without_rechecking_media(self):
        review_token = attach_text_review(source_report(), self.user)["text_review_token"]
        with patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value={"report": text_report(TEXT, [])})), \
             patch("app.api.check_text.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/check-extracted-text", json={"text": TEXT, "review_token": review_token})
        self.assertEqual(response.status_code, 200)
        stored = self.db.added[0].raw_result
        self.assertEqual(verify_pdf_snapshot(response.json()["pdf_snapshot_token"], self.user), stored)
        text = self.extract(self.export(stored))
        for value in (ORIGINAL, TEXT, "Leitura automática original", "Texto confirmado", "não comprova correspondência", "controle.png"):
            self.assertIn(value, text)
        self.assertNotIn("vrev1", text); self.assertNotIn("vpdf1", text)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required")
    def test_link_pdf_keeps_long_input_without_truncating_or_false_media_layers(self):
        source_text = ("Controle fictício de página, sem valor de evidência. " * 95) + "FIMTEXTOCONTROLE"
        report = original_text_report(content_type="url", query_input="https://example.test/original",
            source_url="https://example.test/" + "long-path-" * 350 + "FIMURLCONTROLE", source_text=source_text,
            source_extraction={"method": "static_html", "truncated": True, "rendered_browser": False})
        text = self.extract(self.export(report))
        # Poppler can insert a line break inside an unbroken URL; require the
        # entire final marker after removing layout whitespace, not truncation.
        self.assertIn("FIMURLCONTROLE", "".join(text.split()))
        for value in ("FIMTEXTOCONTROLE", "HTML estático", "não foi analisado", "URL final"):
            self.assertIn(value, text)
        self.assertNotIn("ORIGEM DA MÍDIA", text)
