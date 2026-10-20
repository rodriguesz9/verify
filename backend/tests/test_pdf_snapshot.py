import base64
import asyncio
import copy
import hashlib
import hmac
import json
import re
import shutil
import subprocess
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import JWTError

from helpers import app, fake_user, override_auth_and_db, FakeSession, valid_png
from app.core.security import create_access_token, decode_token
from app.core.request_budget import RequestBudgetMiddleware
from app.services.evidence_policy import media_report
from app.services.pdf_snapshot import attach_pdf_snapshot, verify_pdf_snapshot
from app.services import pdf_snapshot
from app.services.pdf_report_service import display_value, detector_signal, generate_forensic_pdf


def original_report(**overrides):
    report = {**media_report({}), "filename": "evidência.png",
              "file_hash_sha256": hashlib.sha256(valid_png()).hexdigest(),
              "analyzed_at": "2026-10-03T18:30:00+00:00"}
    report.update(overrides)
    return report


def resign(snapshot):
    encoded = base64.urlsafe_b64encode(json.dumps(snapshot).encode()).rstrip(b"=").decode()
    message = f"vpdf1.{encoded}"
    signature = hmac.new(pdf_snapshot._SIGNING_KEY, message.encode(), hashlib.sha256).hexdigest()
    return f"{message}.{signature}"


class PdfSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.key_patch = patch.object(pdf_snapshot, "_SIGNING_KEY", b"independent-test-signing-key-32-bytes")
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def test_anonymous_snapshot_preserves_exact_report_without_mutation(self):
        report = original_report(content_analysis={"summary": "Refutada por duas checagens", "veracity_status": "refuted"})
        before = copy.deepcopy(report)
        result = attach_pdf_snapshot(report, now=1000)
        restored = verify_pdf_snapshot(result["pdf_snapshot_token"], now=1001)
        self.assertEqual(restored, before)
        self.assertEqual(report, before)
        self.assertEqual(result["pdf_snapshot_expires_at"], 4600)

    def test_user_owned_copy_requires_same_active_session(self):
        user = fake_user()
        result = attach_pdf_snapshot(original_report(), user, now=1000)
        token = result["pdf_snapshot_token"]
        self.assertEqual(verify_pdf_snapshot(token, user, now=1001)["filename"], "evidência.png")
        for other in (None, fake_user()):
            with self.subTest(user=other is None), self.assertRaises(HTTPException) as caught:
                verify_pdf_snapshot(token, other, now=1001)
            self.assertEqual(caught.exception.status_code, 403)

    def test_anonymous_capability_is_not_a_login_token(self):
        token = attach_pdf_snapshot(original_report(), now=1000)["pdf_snapshot_token"]
        with self.assertRaises(JWTError):
            decode_token(token)
        with self.assertRaises(HTTPException):
            verify_pdf_snapshot(create_access_token(str(fake_user().id)), now=1001)

    def test_tampered_verdict_is_rejected_before_json_parsing(self):
        token = attach_pdf_snapshot(original_report(), now=1000)["pdf_snapshot_token"]
        prefix, encoded, signature = token.split(".")
        snapshot = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        snapshot["report"]["verdict"] = "Authentic"
        changed = base64.urlsafe_b64encode(json.dumps(snapshot).encode()).rstrip(b"=").decode()
        with patch.object(pdf_snapshot.json, "loads", side_effect=AssertionError("Unverified JSON parsed")):
            with self.assertRaises(HTTPException) as caught:
                verify_pdf_snapshot(f"{prefix}.{changed}.{signature}", now=1001)
        self.assertEqual(caught.exception.status_code, 422)

    def test_expired_token_is_rejected_at_expiry_boundary(self):
        token = attach_pdf_snapshot(original_report(), now=1000)["pdf_snapshot_token"]
        self.assertEqual(verify_pdf_snapshot(token, now=4599)["verdict"], "Suspicious")
        with self.assertRaises(HTTPException) as caught:
            verify_pdf_snapshot(token, now=4600)
        self.assertEqual(caught.exception.status_code, 410)

    def test_future_issuance_is_rejected(self):
        token = attach_pdf_snapshot(original_report(), now=2000)["pdf_snapshot_token"]
        with self.assertRaises(HTTPException) as caught:
            verify_pdf_snapshot(token, now=1000)
        self.assertEqual(caught.exception.status_code, 422)

    def test_signed_wrong_purpose_schema_and_lifetime_fail_closed(self):
        result = attach_pdf_snapshot(original_report(), now=1000)
        encoded = result["pdf_snapshot_token"].split(".")[1]
        original = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        changes = ({"purpose": "login"}, {"version": 2}, {"owner": "not-a-user"},
                   {"exp": 9000}, {"iat": True}, {"extra": "unsigned"}, {"report": {}})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(HTTPException) as caught:
                verify_pdf_snapshot(resign({**original, **change}), now=1001)
            self.assertEqual(caught.exception.status_code, 422)

    def test_missing_signing_configuration_disables_only_export(self):
        with patch.object(pdf_snapshot, "_SIGNING_KEY", None):
            result = attach_pdf_snapshot(original_report())
            self.assertEqual(result["pdf_export_status"], "unavailable")
            self.assertNotIn("pdf_snapshot_token", result)
            with self.assertRaises(HTTPException) as caught:
                verify_pdf_snapshot("anything")
        self.assertEqual(caught.exception.status_code, 503)

    def test_large_report_is_not_truncated_or_signed(self):
        report = original_report(summary="x" * pdf_snapshot.MAX_SNAPSHOT_PAYLOAD_BYTES)
        result = attach_pdf_snapshot(report)
        self.assertEqual(result["summary"], report["summary"])
        self.assertEqual(result["pdf_export_status"], "unavailable")
        self.assertNotIn("pdf_snapshot_token", result)

    def test_large_or_malformed_token_is_rejected_before_decode(self):
        for token in (None, {}, "vpdf1.bad.bad", "x" * (pdf_snapshot.MAX_SNAPSHOT_TOKEN_BYTES + 1)):
            with self.subTest(type=type(token).__name__), patch.object(pdf_snapshot.base64, "b64decode", side_effect=AssertionError("Decoded unsafe input")):
                with self.assertRaises(HTTPException):
                    verify_pdf_snapshot(token)

    def test_history_refresh_strips_old_tokens_and_preserves_original_time(self):
        first = attach_pdf_snapshot(original_report(), now=1000)
        second = attach_pdf_snapshot(first, now=5000)
        self.assertNotEqual(first["pdf_snapshot_token"], second["pdf_snapshot_token"])
        report = verify_pdf_snapshot(second["pdf_snapshot_token"], now=5001)
        self.assertEqual(report["analyzed_at"], "2026-10-03T18:30:00+00:00")
        self.assertFalse(any(key.startswith("pdf_") for key in report))

    def test_legacy_without_original_sha_is_explicitly_unavailable(self):
        legacy = media_report({})
        self.assertEqual(attach_pdf_snapshot(legacy)["pdf_export_status"], "unavailable")

    def test_malformed_legacy_report_is_unavailable_not_server_error(self):
        for report in (None, [], "legacy", 42, {1: "invalid"}, original_report(content_type=[])):
            with self.subTest(type=type(report).__name__):
                result = attach_pdf_snapshot(report)
                self.assertEqual(result["pdf_export_status"], "unavailable")
                self.assertNotIn("pdf_snapshot_token", result)


class PdfExportEndpointTests(unittest.TestCase):
    def setUp(self):
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)
        self.addCleanup(self.client.close)
        self.key_patch = patch.object(pdf_snapshot, "_SIGNING_KEY", b"independent-test-signing-key-32-bytes")
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def test_saved_result_export_never_calls_quota_media_or_provider(self):
        original = original_report()
        result = attach_pdf_snapshot(original, self.user)
        with patch("app.api.verificacao.analyze_media", new=AsyncMock(side_effect=AssertionError("Reanalysis"))) as analyze, \
             patch("app.api.verificacao.verify_limit", new=AsyncMock(side_effect=AssertionError("Quota charged"))) as limit, \
             patch("app.api.verificacao.read_media", new=AsyncMock(side_effect=AssertionError("File read"))) as read, \
             patch("app.api.verificacao.generate_forensic_pdf", return_value=b"%PDF-original") as render:
            response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": result["pdf_snapshot_token"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-original")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(render.call_args.args[0]["analyzed_at"], original["analyzed_at"])
        self.assertEqual(render.call_args.args[0]["verdict"], original["verdict"])
        self.assertEqual(render.call_args.args[1:], (original["filename"], original["file_hash_sha256"]))
        analyze.assert_not_awaited(); limit.assert_not_awaited(); read.assert_not_awaited()
        self.assertEqual(self.db.commits, 0)

    def test_old_file_only_and_unsigned_result_are_rejected_without_analysis(self):
        with patch("app.api.verificacao.analyze_media", new=AsyncMock(side_effect=AssertionError("Reanalysis"))) as analyze:
            old = self.client.post("/api/verificar/relatorio-pdf", files={"file": ("a.png", valid_png(), "image/png")})
            forged = self.client.post("/api/verificar/relatorio-pdf", json=original_report(verdict="Authentic"))
            extra = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": "invalid", "filename": "other.png"})
        self.assertEqual([old.status_code, forged.status_code, extra.status_code], [422, 422, 422])
        analyze.assert_not_awaited()

    def test_request_body_over_limit_is_rejected(self):
        response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": "x" * (pdf_snapshot.MAX_SNAPSHOT_BODY_BYTES + 1)})
        self.assertEqual(response.status_code, 413)

    def test_authenticated_upload_saves_original_metadata_not_export_token(self):
        canonical = media_report({})
        with patch("app.api.upload.analyze_media", new=AsyncMock(return_value=canonical)), \
             patch("app.api.upload.verify_limit", new=AsyncMock()):
            response = self.client.post("/api/upload", files={"file": ("controle.png", valid_png(), "image/png")})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["pdf_export_status"], "ready")
        stored = self.db.added[0].raw_result
        self.assertEqual(stored["filename"], "controle.png")
        self.assertEqual(stored["file_hash_sha256"], hashlib.sha256(valid_png()).hexdigest())
        self.assertFalse(any(key.startswith("pdf_") for key in stored))
        self.assertEqual(verify_pdf_snapshot(result["pdf_snapshot_token"], self.user), stored)

    def test_anonymous_full_analysis_exports_without_server_snapshot_storage(self):
        override_auth_and_db(None, self.db)
        with patch("app.api.verificacao.analyze_media", new=AsyncMock(return_value=media_report({}))):
            response = self.client.post("/api/verificar/completo", files={"file": ("controle.png", valid_png(), "image/png")})
        self.assertEqual(response.status_code, 200)
        token = response.json()["pdf_snapshot_token"]
        pdf = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": token})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(self.db.added, [])
        self.assertEqual(self.db.commits, 0)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required for PDF text fidelity check")
    def test_pdf_keeps_veracity_sources_limits_and_original_time(self):
        content = {"veracity_status": "refuted", "summary": "A afirmação foi refutada.",
                   "claim_assessments": [{"claim": "Afirmação de controle", "status": "refuted", "explanation": "Duas checagens correspondentes.",
                       "evidence": [{"publisher": "Fonte de controle", "url": "https://example.com/controle", "rating": "Falso", "review_date": "2026-10-01"}],
                       "excluded_evidence": [{"publisher": "Fonte diferente", "exclusion_reason": "Afirmação diferente", "url": "https://example.com/excluida"}]}],
                   "limitations": ["OCR pode conter erros."]}
        result = attach_pdf_snapshot(original_report(content_analysis=content), self.user)
        response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": result["pdf_snapshot_token"]})
        self.assertEqual(response.status_code, 200)
        extracted = subprocess.run(["pdftotext", "-", "-"], input=response.content, capture_output=True, check=True).stdout.decode()
        for value in ("2026-10-03T18:30:00+00:00", "Verificada como falsa nas fontes consultadas", "Fonte de controle", "Fonte diferente", "Afirmação diferente", "OCR pode conter erros", "Precisão não calibrada"):
            self.assertIn(value, extracted)
        self.assertNotIn("vpdf1", extracted)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required for PDF text fidelity check")
    def test_pdf_translates_statuses_without_changing_signed_report(self):
        report = original_report(analysis_status="partial", authenticity_status="inconclusive",
                                 content_analysis={"veracity_status": "inconclusive", "summary": "Controle sem conclusão."})
        result = attach_pdf_snapshot(report, self.user)
        response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": result["pdf_snapshot_token"]})
        self.assertEqual(response.status_code, 200)
        extracted = subprocess.run(["pdftotext", "-", "-"], input=response.content, capture_output=True, check=True).stdout.decode()
        self.assertIn("Estado da análise: Parcial (cobertura limitada)", extracted)
        self.assertIn("Origem/autenticidade: Inconclusivo", extracted)
        self.assertIn("Veracidade do conteúdo: Inconclusivo", extracted)
        self.assertNotIn("partial", extracted)
        self.assertNotIn("inconclusive", extracted)
        self.assertEqual(verify_pdf_snapshot(result["pdf_snapshot_token"], self.user), report)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required for PDF text fidelity check")
    def test_long_signed_report_flows_across_pages_without_evidence_truncation(self):
        explanation = "Explicação longa de controle, sem afirmação de precisão. " * 350 + "FIMRESUMOCONTROLE"
        metadata = "Metadados de controle com limitações documentadas. " * 350 + "FIMMETADADOSCONTROLE"
        context = "Pesquisa de proveniência sem confirmação de origem. " * 350 + "FIMPROVENIENCIACONTROLE"
        extracted_text = "Texto extraído de controle para revisão humana. " * 160 + "FIMEXTRACAOCONTROLE"
        source_url = "https://example.com/" + "long-control-path-" * 300 + "FIMFONTECONTROLE"
        content = {"veracity_status": "unverified", "summary": "Nenhuma conclusão sobre a veracidade.",
                   "claim_assessments": [{"claim": "Afirmação de controle", "status": "unverified",
                       "explanation": "Fonte sem correspondência suficiente.", "evidence": [],
                       "excluded_evidence": [{"publisher": "Fonte de controle", "url": source_url,
                           "exclusion_reason": "Afirmação diferente."}]}]}
        for mode in ("ocr", "transcription"):
            with self.subTest(extraction=mode):
                report = original_report(filename="W" * 251 + ".png", summary=explanation,
                    plain_explanation=explanation, content_analysis=content,
                    forensics={"metadata": {"summary": metadata}, "context": {"wayback": {"summary": context}},
                               "ocr": {"text": extracted_text if mode == "ocr" else ""}},
                    transcription=extracted_text if mode == "transcription" else "")
                result = attach_pdf_snapshot(report, self.user)
                self.assertEqual(result["pdf_export_status"], "ready")
                response = self.client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": result["pdf_snapshot_token"]})
                self.assertEqual(response.status_code, 200)
                self.assertGreater(len(re.findall(rb"/Type\s*/Page\b", response.content)), 1)
                extracted = subprocess.run(["pdftotext", "-", "-"], input=response.content, capture_output=True, check=True).stdout.decode()
                for end_marker in ("FIMRESUMOCONTROLE", "FIMMETADADOSCONTROLE", "FIMPROVENIENCIACONTROLE", "FIMEXTRACAOCONTROLE", "FIMFONTECONTROLE"):
                    self.assertIn(end_marker, extracted)
                self.assertNotIn("vpdf1", extracted)


class PdfExportAdmissionTests(unittest.TestCase):
    def test_declared_large_export_body_is_rejected_before_reading(self):
        handler, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
        middleware = RequestBudgetMiddleware(handler, per_ip=10, global_limit=20, max_body=35 * 1024 * 1024)
        scope = {"type": "http", "method": "POST", "path": "/api/verificar/relatorio-pdf",
                 "headers": [(b"content-length", str(pdf_snapshot.MAX_SNAPSHOT_BODY_BYTES + 1).encode())],
                 "client": ("fixture", 1)}
        asyncio.run(middleware(scope, receive, send))
        self.assertEqual(send.call_args_list[0].args[0]["status"], 413)
        handler.assert_not_awaited(); receive.assert_not_awaited()
        self.assertEqual(middleware.active, 0)

    def test_chunked_export_body_is_rejected_before_handler_or_providers(self):
        handler, send = AsyncMock(), AsyncMock()
        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": b"x" * pdf_snapshot.MAX_SNAPSHOT_BODY_BYTES, "more_body": True},
            {"type": "http.request", "body": b"x", "more_body": True},
        ])
        middleware = RequestBudgetMiddleware(handler, per_ip=10, global_limit=20, max_body=35 * 1024 * 1024)
        scope = {"type": "http", "method": "POST", "path": "/api/verificar/relatorio-pdf",
                 "headers": [], "client": ("fixture", 1)}
        asyncio.run(middleware(scope, receive, send))
        self.assertEqual(send.call_args_list[0].args[0]["status"], 413)
        self.assertEqual(receive.await_count, 2)
        handler.assert_not_awaited()
        self.assertEqual(middleware.active, 0)


class PdfPresentationTests(unittest.TestCase):
    def test_missing_value_formatting_never_replaces_valid_zero_or_false(self):
        for missing in (None, "", "  "):
            self.assertEqual(display_value(missing), "Não disponível")
        self.assertEqual(display_value(0), "0")
        self.assertEqual(display_value(False), "False")
        self.assertEqual(display_value("None é um texto literal"), "None é um texto literal")
        for invalid in (None, True, "0.99", -1, 2, float("nan"), float("inf")):
            self.assertEqual(detector_signal(invalid), "não disponível")
        for valid in (0, .999999, 1):
            self.assertEqual(detector_signal(valid), str(valid))

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler required for PDF presentation check")
    def test_nullable_fields_do_not_print_none_or_fabricate_signals(self):
        report = original_report(policy_version=None, analysis_status=None, authenticity_status=None,
            summary=None, explicacao_leiga=None, explicacao_forense=None,
            metadata={"summary": None}, contexto={"wayback": {"summary": None}},
            content_analysis={"status": "pending_user_review", "veracity_status": None, "summary": None, "claim_assessments": [{
                "claim": "Controle fictício; não é checagem real.", "status": None, "explanation": None,
                "evidence": [{"publisher": None, "publisher_family": "Família de controle", "url": None,
                              "rating": None, "review_date": None}],
                "excluded_evidence": [{"publisher": None, "url": "https://example.com/excluida", "exclusion_reason": None}],
            }]},
            provider_coverage={"sightengine": {"status": "success", "ai_score": 0, "deepfake_score": None},
                               "hive": {"status": "not_configured", "ai_score": None, "deepfake_score": None}},
            forensics={"video": {"sampled_frames": None, "timestamps_seconds": None}})
        before = copy.deepcopy(report)
        pdf = generate_forensic_pdf(report, report["filename"], report["file_hash_sha256"])
        extracted = subprocess.run(["pdftotext", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()
        self.assertNotIn("None", extracted)
        self.assertIn("sinal IA: 0; sinal facial: não disponível", extracted)
        self.assertIn("hive: Não configurada - sinal IA: não disponível", extracted)
        self.assertIn("Escala dos sinais: 0 a 1", extracted)
        self.assertEqual(extracted.count("Escala dos sinais"), 1)
        self.assertIn("Estado da checagem do conteúdo: Aguarda conferência do texto", extracted)
        self.assertIn("Origem/autenticidade: Origem indeterminada", extracted)
        self.assertIn("Veracidade do conteúdo: Evidência insuficiente", extracted)
        self.assertIn("Família de controle", extracted)
        self.assertIn("Data: Não disponível", extracted)
        self.assertIn("não informado quadros amostrados", extracted)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
