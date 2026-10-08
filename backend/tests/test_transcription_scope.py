"""Offline ownership/context regressions; no provider jobs or private env."""

import asyncio
import base64
import copy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import app, FakeSession, fake_user, override_auth_and_db, valid_wav
from app.services import transcription_scope as ownership
from app.services.evidence_policy import media_report
from app.services.media_validation import ValidatedMedia
from app.services.pdf_snapshot import verify_pdf_snapshot
from app.services.whatsapp_security import ReceiptGuard, parse_message


NONCE_A = "a" * 32
NONCE_B = "b" * 32
WEBHOOK_SECRET = "offline-webhook-test-only-" + "c" * 32


def request_with(nonce=None):
    headers = {} if nonce is None else {ownership.SCOPE_HEADER: nonce}
    return SimpleNamespace(headers=headers)


def speech_report(status="success"):
    audio = {
        "available": status == "success",
        "transcription": "Não pague R$ 123,45 em 07/10/2026." if status == "success" else "",
        "transcription_detail": {"status": status, "provider": "assemblyai"},
    }
    return media_report({"audio": audio}, "audio")


def webhook_body(message_id="offline-receipt-001", sender="sender-one@example.invalid"):
    return {
        "event": "messages.upsert", "instance": "offline-test-instance",
        "data": {
            "key": {"id": message_id, "remoteJid": sender, "fromMe": False},
            "message": {"audioMessage": {
                "mimetype": "audio/wav",
                "base64": base64.b64encode(valid_wav()).decode("ascii"),
            }},
        },
    }


class RequestTranscriptionScopeTests(unittest.TestCase):
    def test_missing_or_invalid_anonymous_nonce_disables_reuse(self):
        for nonce in (None, "", "a" * 31, "a" * 33, "A" * 32,
                      "g" * 32, " " + NONCE_A, NONCE_A + "\n", 123, []):
            with self.subTest(nonce_type=type(nonce).__name__):
                self.assertIsNone(ownership.request_transcription_scope(request_with(nonce)))

    def test_valid_anonymous_nonce_is_stable_distinct_and_opaque(self):
        first = ownership.request_transcription_scope(request_with(NONCE_A))
        self.assertRegex(first, r"^[a-f0-9]{64}$")
        self.assertEqual(first, ownership.request_transcription_scope(request_with(NONCE_A)))
        self.assertNotEqual(first, ownership.request_transcription_scope(request_with(NONCE_B)))
        self.assertNotIn(NONCE_A, first)

    def test_verified_account_always_overrides_anonymous_header(self):
        user = fake_user()
        scopes = [ownership.request_transcription_scope(request_with(nonce), user)
                  for nonce in (None, NONCE_A, NONCE_B, "invalid")]
        self.assertEqual(len(set(scopes)), 1)
        self.assertRegex(scopes[0], r"^[a-f0-9]{64}$")
        self.assertNotIn(str(user.id), scopes[0])
        self.assertNotEqual(scopes[0], ownership.request_transcription_scope(request_with(NONCE_A)))
        self.assertNotEqual(scopes[0], ownership.request_transcription_scope(request_with(NONCE_A), fake_user()))

    def test_webhook_receipt_is_stable_distinct_and_not_anonymous_identity(self):
        receipt = "a" * 64
        namespace = ownership.webhook_transcription_scope(receipt)
        self.assertRegex(namespace, r"^[a-f0-9]{64}$")
        self.assertEqual(namespace, ownership.webhook_transcription_scope(receipt))
        self.assertNotEqual(namespace, ownership.webhook_transcription_scope("b" * 64))
        self.assertNotEqual(namespace, ownership.request_transcription_scope(request_with(NONCE_A)))
        self.assertNotEqual(namespace, receipt)
        for value in (None, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64, receipt + "\n"):
            self.assertIsNone(ownership.webhook_transcription_scope(value))

    def test_only_transcription_pending_states_request_resumption(self):
        for status in ownership.PENDING_STATUSES:
            self.assertTrue(ownership.has_pending_transcription({"transcription_detail": {"status": status}}))
            self.assertTrue(ownership.has_pending_transcription(speech_report(status)))
        for report in (None, [], {}, {"forensics": []}, {"forensics": {"audio": []}},
                       {"transcription_detail": []}, speech_report("success"), speech_report("no_speech"),
                       {"forensics": {"hive": {"status": "pending"}, "gemini_vision": {"status": "pending"}}}):
            self.assertFalse(ownership.has_pending_transcription(report))


class TranscriptionContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_nested_scope_restores_after_normal_and_exception_paths(self):
        self.assertIsNone(ownership.current_transcription_scope())
        with ownership.transcription_scope("outer-control"):
            self.assertEqual(ownership.current_transcription_scope(), "outer-control")
            with ownership.transcription_scope("inner-control"):
                self.assertEqual(ownership.current_transcription_scope(), "inner-control")
            self.assertEqual(ownership.current_transcription_scope(), "outer-control")
            with self.assertRaisesRegex(RuntimeError, "offline control"):
                with ownership.transcription_scope("exception-control"):
                    raise RuntimeError("offline control")
            self.assertEqual(ownership.current_transcription_scope(), "outer-control")
            with ownership.transcription_scope(None):
                self.assertIsNone(ownership.current_transcription_scope())
            self.assertEqual(ownership.current_transcription_scope(), "outer-control")
        self.assertIsNone(ownership.current_transcription_scope())

    async def test_cancellation_resets_child_scope_without_changing_parent(self):
        entered = asyncio.Event()
        never_ready = asyncio.Event()
        observed_after_cancel = []

        async def worker():
            try:
                with ownership.transcription_scope("cancelled-child"):
                    entered.set()
                    await never_ready.wait()
            except asyncio.CancelledError:
                observed_after_cancel.append(ownership.current_transcription_scope())
                raise

        with ownership.transcription_scope("parent-control"):
            task = asyncio.create_task(worker())
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(observed_after_cancel, ["parent-control"])
            self.assertEqual(ownership.current_transcription_scope(), "parent-control")
        self.assertIsNone(ownership.current_transcription_scope())

    async def test_gather_inherits_request_scope_but_child_updates_are_isolated(self):
        async def child(label):
            inherited = ownership.current_transcription_scope()
            with ownership.transcription_scope(label):
                await asyncio.sleep(0)
                own = ownership.current_transcription_scope()
            return inherited, own, ownership.current_transcription_scope()

        with ownership.transcription_scope("request-control"):
            results = await asyncio.gather(child("child-one"), child("child-two"))
            self.assertEqual(results, [
                ("request-control", "child-one", "request-control"),
                ("request-control", "child-two", "request-control"),
            ])
            self.assertEqual(ownership.current_transcription_scope(), "request-control")
        self.assertIsNone(ownership.current_transcription_scope())


class TranscriptionScopeEndpointTests(unittest.TestCase):
    def setUp(self):
        self.user = None
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.media = ValidatedMedia(valid_wav(), "offline-control.wav", "audio/wav", "audio", {})
        self.scopes = []
        self.reports = []
        self.headers = {ownership.SCOPE_HEADER: NONCE_A}

        async def analyze(_media, **_kwargs):
            self.scopes.append(ownership.current_transcription_scope())
            return copy.deepcopy(self.reports.pop(0) if self.reports else speech_report())

        for target in ("app.api.upload.analyze_media", "app.api.verificacao.analyze_media",
                       "app.api.whatsapp.analyze_validated_media"):
            self.enterContext(patch(target, new=AsyncMock(side_effect=analyze)))
        for target in ("app.api.upload.read_media", "app.api.verificacao.read_media",
                       "app.api.whatsapp.validate_media"):
            self.enterContext(patch(target, new=AsyncMock(return_value=self.media)))
        self.enterContext(patch("app.api.whatsapp.download_media", new=AsyncMock(return_value=self.media.data)))
        for target in ("app.api.upload.verify_limit", "app.api.verificacao.verify_limit"):
            self.enterContext(patch(target, new=AsyncMock()))
        self.history = self.enterContext(patch("app.api.whatsapp.save_anonymous_history", new=AsyncMock()))
        self.tts = self.enterContext(patch("app.api.whatsapp.get_ai_voice_speech", new=AsyncMock(return_value={"available": False})))
        self.enterContext(patch("app.api.whatsapp.receipts", new=ReceiptGuard()))
        self.enterContext(patch.dict(os.environ, {
            "WHATSAPP_BOT_ENABLED": "true", "WHATSAPP_WEBHOOK_SECRET": WEBHOOK_SECRET,
        }))

    def assert_private_report(self, report, *private_values):
        forbidden = {"namespace", "transcription_scope", "asr_scope", "scope_namespace",
                     "resume_namespace", "job_id", "transcript_id", "receipt_key"}

        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(report)
        serialized = json.dumps(report)
        for private in (NONCE_A, NONCE_B, *private_values):
            if private:
                self.assertNotIn(private, serialized)

    def assert_scoped_response(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        expected = ownership.request_transcription_scope(request_with(NONCE_A), self.user)
        self.assertEqual(self.scopes[-1], expected)
        self.assertIsNone(ownership.current_transcription_scope())
        self.assert_private_report(response.json(), expected)
        if response.json().get("pdf_snapshot_token"):
            self.assert_private_report(verify_pdf_snapshot(response.json()["pdf_snapshot_token"], self.user), expected)
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def post_media(self, path, headers=None):
        return self.client.post(path, headers=self.headers if headers is None else headers,
                                files={"file": ("offline-control.wav", self.media.data, "audio/wav")})

    def test_upload_receives_request_scope_without_reflecting_ids(self):
        self.assert_scoped_response(self.post_media("/api/upload"))

    def test_full_verification_receives_request_scope_without_reflecting_ids(self):
        self.assert_scoped_response(self.post_media("/api/verificar/completo"))

    def test_quick_audio_receives_request_scope_without_reflecting_ids(self):
        self.assert_scoped_response(self.post_media("/api/verificar/audio-rapido"))

    def test_simulator_receives_request_scope_without_reflecting_ids(self):
        response = self.client.post("/api/whatsapp/simulate", headers=self.headers, json={
            "media_url": "https://example.invalid/authorized-control.wav", "media_type": "audio",
            "from_number": "untrusted-simulator-owner", "message": "",
        })
        self.assert_scoped_response(response)
        self.assert_private_report(response.json(), "untrusted-simulator-owner")
        self.history.assert_not_awaited()

    def test_authenticated_webhook_receives_receipt_scope_not_public_nonce(self):
        body = webhook_body()
        receipt = parse_message(body).receipt_key
        expected = ownership.webhook_transcription_scope(receipt)
        response = self.client.post("/api/whatsapp/webhook", json=body, headers={
            **self.headers, "X-Verify-Webhook-Secret": WEBHOOK_SECRET,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(self.scopes, [expected])
        self.assertNotEqual(expected, ownership.request_transcription_scope(request_with(NONCE_A)))
        self.assert_private_report(response.json(), expected, receipt, "offline-receipt-001", "sender-one@example.invalid")
        self.assertIsNone(ownership.current_transcription_scope())

    def test_upload_missing_or_invalid_nonce_has_no_cross_request_scope(self):
        for headers in ({}, {ownership.SCOPE_HEADER: "invalid"}):
            response = self.post_media("/api/upload", headers=headers)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.scopes, [None, None])

    def test_account_scope_overrides_header_and_stored_raw_result_has_no_namespace(self):
        self.user = fake_user()
        override_auth_and_db(self.user, self.db)
        self.assert_scoped_response(self.post_media("/api/upload"))
        response = self.post_media("/api/upload", headers={ownership.SCOPE_HEADER: NONCE_B})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.scopes[0], self.scopes[1])
        for record in self.db.added:
            if hasattr(record, "raw_result"):
                self.assert_private_report(record.raw_result, self.scopes[0], str(self.user.id))

    def test_simulator_never_treats_from_number_as_owner(self):
        payload = {"media_url": "https://example.invalid/control.wav", "media_type": "audio", "message": ""}
        for sender in ("same-untrusted-number", "same-untrusted-number", "different-untrusted-number"):
            response = self.client.post("/api/whatsapp/simulate", json={**payload, "from_number": sender})
            self.assertEqual(response.status_code, 200)
            self.assert_private_report(response.json(), sender)
        self.assertEqual(self.scopes, [None, None, None])
        for sender in ("sender-one", "sender-two"):
            response = self.client.post("/api/whatsapp/simulate", headers=self.headers,
                                        json={**payload, "from_number": sender})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.scopes[-2], self.scopes[-1])
        self.assertIsNotNone(self.scopes[-1])
        self.history.assert_not_awaited()

    def test_same_authenticated_receipt_pending_then_success_resumes_then_deduplicates(self):
        self.reports = [speech_report("pending"), speech_report("success")]
        body = webhook_body("offline-pending-receipt")
        body["want_voice_reply"] = True
        headers = {"X-Verify-Webhook-Secret": WEBHOOK_SECRET}
        first = self.client.post("/api/whatsapp/webhook", json=body, headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "pending")
        self.history.assert_not_awaited()
        self.tts.assert_not_awaited()
        second = self.client.post("/api/whatsapp/webhook", json=body, headers=headers)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "success")
        third = self.client.post("/api/whatsapp/webhook", json=body, headers=headers)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.json(), {"status": "duplicate", "reply": ""})
        self.assertEqual(len(self.scopes), 2)
        self.assertIsNotNone(self.scopes[0])
        self.assertEqual(self.scopes[0], self.scopes[1])
        self.history.assert_awaited_once()
        self.tts.assert_awaited_once()
        for response in (first, second, third):
            self.assert_private_report(response.json(), *self.scopes, parse_message(body).receipt_key,
                                       "offline-pending-receipt")
        self.assertIsNone(ownership.current_transcription_scope())

    def test_webhook_authentication_precedes_analysis_and_scope_assignment(self):
        response = self.client.post("/api/whatsapp/webhook", json=webhook_body(), headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.scopes, [])
        self.history.assert_not_awaited()
        self.assertIsNone(ownership.current_transcription_scope())


if __name__ == "__main__":
    unittest.main()
