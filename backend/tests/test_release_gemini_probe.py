"""Offline diagnostics safety: no environment files or real providers accessed."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from scripts import release_gemini_probe as probe


CLIENT = httpx.AsyncClient


def success_payload(text):
    return {"modelVersion": probe.MODEL, "candidates": [{"finishReason": "STOP",
        "content": {"parts": [{"text": text}]}}]}


class ProbeSafetyTests(unittest.IsolatedAsyncioTestCase):
    def args(self, directory, **changes):
        values = {"free_credits_confirmed": True, "model": probe.MODEL, "cases": "text,ocr",
                  "prior_ui_attempts": 4, "output": str(Path(directory) / "diagnostics.json"),
                  "env_file": "/not-read/private.env"}
        values.update(changes)
        return SimpleNamespace(**values)

    async def test_missing_opt_in_never_reads_key_or_sends_request(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values") as config, \
                patch.object(probe, "probe_once", new=AsyncMock()) as remote:
            with self.assertRaises(ValueError):
                await probe.main(self.args(directory, free_credits_confirmed=False))
        config.assert_not_called()
        remote.assert_not_called()

    async def test_invalid_models_or_repeated_controls_never_read_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            for changes in [{"model": "gemini-paid-model"}, {"cases": "text,text"}, {"cases": "text,ocr,text"}]:
                with self.subTest(changes=changes), patch.object(probe, "dotenv_values") as config:
                    with self.assertRaises(ValueError):
                        await probe.main(self.args(directory, **changes))
                    config.assert_not_called()

    async def test_exactly_two_calls_logged_separately_no_secret_in_artifact_or_stdout(self):
        result = {"provider": "gemini", "status": "success", "available": True}
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values", return_value={
                "GEMINI_API_KEY": "test-key-not-for-output", "DATABASE_URL": "private-db-not-for-output"}) as config, \
                patch.object(probe, "probe_once", new=AsyncMock(return_value=result)) as remote:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                await probe.main(self.args(directory))
            config.assert_called_once_with("/not-read/private.env", interpolate=False)
            self.assertEqual(remote.await_count, 2)
            record = json.loads(Path(directory, "diagnostics.json").read_text())
            self.assertEqual(record["request_accounting"]["diagnostic_generations_started"], 2)
            self.assertEqual(record["request_accounting"]["combined_reported_generation_ceiling"], 6)
            self.assertEqual([item.args[2] for item in remote.await_args_list], ["text", "ocr"])
            for private in ["test-key-not-for-output", "private-db-not-for-output"]:
                self.assertNotIn(private, stdout.getvalue())
                self.assertNotIn(private, json.dumps(record))

    async def test_existing_reservation_refuses_rerun_before_reading_key(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "gemini-request-ledger.json").write_text("{}")
            with patch.object(probe, "dotenv_values") as config:
                with self.assertRaises(ValueError):
                    await probe.main(self.args(directory))
            config.assert_not_called()

    async def test_no_key_refuses_all_requests(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values", return_value={}), \
                patch.object(probe, "probe_once", new=AsyncMock()) as remote:
            with self.assertRaises(ValueError):
                await probe.main(self.args(directory))
        remote.assert_not_called()

    async def test_single_request_http_error_is_classified_without_printing_provider_body(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT",
                "message": "Thinking configuration not supported. private-key-debug"}}, request=request)
        def factory(**kwargs):
            self.assertFalse(kwargs["trust_env"])
            self.assertFalse(kwargs["follow_redirects"])
            return CLIENT(transport=httpx.MockTransport(handler), **kwargs)
        with patch.object(probe.httpx, "AsyncClient", side_effect=factory):
            result = await probe.probe_once("test-key-only", probe.MODEL, "text", probe.control_body("text"))
        self.assertEqual(len(requests), 1)
        self.assertEqual(result["http_status"], 400)
        self.assertEqual(result["reason_class"], "unsupported_thinking_configuration")
        self.assertNotIn("private-key-debug", json.dumps(result))

    async def test_transport_timeout_no_retry_or_exception_leak(self):
        attempts = []
        def handler(request):
            attempts.append(1)
            raise httpx.ReadTimeout("private-key-debug", request=request)
        with patch.object(probe.httpx, "AsyncClient", side_effect=lambda **kwargs:
                CLIENT(transport=httpx.MockTransport(handler), **kwargs)):
            result = await probe.probe_once("test-key-only", probe.MODEL, "text", probe.control_body("text"))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result["status"], "timeout")
        self.assertNotIn("private-key-debug", json.dumps(result))

    def test_literal_ocr_records_matches_not_original_provider_text(self):
        result = probe.summarize_payload(success_payload(json.dumps({"text": probe.REFERENCE})), "ocr")
        self.assertTrue(result["exact_reference_match"])
        self.assertTrue(result["negation_literal_preserved"])
        self.assertTrue(result["amount_literal_preserved"])
        self.assertTrue(result["date_literal_preserved"])
        self.assertNotIn("Nao pague", json.dumps(result))

    def test_numeric_true_is_not_a_successful_boolean_control(self):
        result = probe.summarize_payload(success_payload('{"ok":1}'), "text")
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "control_mismatch")

    def test_incomplete_generation_cannot_claim_success(self):
        payload = success_payload('{"ok":true}')
        payload["candidates"][0]["finishReason"] = "MAX_TOKENS"
        result = probe.summarize_payload(payload, "text")
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "incomplete_generation")
        self.assertEqual(result["finish_reason"], "MAX_TOKENS")

    def test_untrusted_metadata_is_allowlisted_not_echoed(self):
        payload = success_payload('{"ok":true}')
        payload.update(modelVersion="private-key-debug", usageMetadata={"promptTokenCount": "private-key-debug",
            "candidatesTokenCount": 1, "thoughtsTokenCount": True, "totalTokenCount": -1})
        result = probe.summarize_payload(payload, "text")
        self.assertEqual(result["token_usage"], {"candidatesTokenCount": 1})
        self.assertNotIn("private-key-debug", json.dumps(result))

    def test_request_config_has_fixed_endpoint_model_and_no_other_tools(self):
        text = probe.control_body("text")
        image = probe.control_body("ocr")
        self.assertEqual(text["generationConfig"]["thinkingConfig"], {"thinkingLevel": "LOW"})
        self.assertEqual(len(image["contents"][0]["parts"]), 2)
        self.assertNotIn("tools", text)
        self.assertEqual(probe.parser().get_default("cases"), "text,ocr")


if __name__ == "__main__":
    unittest.main()
