"""Offline safety of the fixed-credit probe; no private env or live API read."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from scripts import release_hive_probe as probe


CLIENT = httpx.AsyncClient


class HiveProbeSafetyTests(unittest.IsolatedAsyncioTestCase):
    def args(self, directory, **changes):
        values = {"existing_credit_confirmed": True, "env_file": "/not-read/private.env",
                  "output": str(Path(directory) / "controls.json")}
        values.update(changes)
        return SimpleNamespace(**values)

    async def test_without_authorization_never_reads_key_or_sends(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values") as config, \
             patch.object(probe, "probe_once", new=AsyncMock()) as remote:
            with self.assertRaises(ValueError):
                await probe.main(self.args(directory, existing_credit_confirmed=False))
        config.assert_not_called()
        remote.assert_not_called()

    async def test_existing_ledger_refuses_new_output_in_same_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "hive-request-ledger.json").write_text("{}")
            with patch.object(probe, "dotenv_values") as config, patch.object(probe, "probe_once", new=AsyncMock()) as remote:
                with self.assertRaises(ValueError):
                    await probe.main(self.args(directory, output=str(Path(directory, "different.json"))))
            config.assert_not_called()
            remote.assert_not_called()

    async def test_existing_output_or_symlink_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "controls.json")
            output.write_text("preserve")
            with patch.object(probe, "dotenv_values") as config:
                with self.assertRaises(ValueError):
                    await probe.main(self.args(directory))
            self.assertEqual(output.read_text(), "preserve")
            config.assert_not_called()
            output.unlink()
            output.symlink_to(Path(directory, "absent.json"))
            with patch.object(probe, "dotenv_values") as config:
                with self.assertRaises(ValueError):
                    await probe.main(self.args(directory))
            config.assert_not_called()

    async def test_public_output_directory_is_rejected_before_key_read(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory).chmod(0o755)
            with patch.object(probe, "dotenv_values") as config:
                with self.assertRaises(ValueError):
                    await probe.main(self.args(directory))
            config.assert_not_called()

    async def test_changed_fixture_is_rejected_before_key_read_or_http(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(Path, "read_bytes", return_value=b"changed-control"), \
             patch.object(probe, "dotenv_values") as config, patch.object(probe, "probe_once", new=AsyncMock()) as remote:
            with self.assertRaises(ValueError):
                await probe.main(self.args(directory))
        config.assert_not_called()
        remote.assert_not_called()

    async def test_exact_two_calls_reserved_before_http_no_env_injection_or_secret_output(self):
        environment_before = dict(os.environ)
        results = []
        with tempfile.TemporaryDirectory() as directory:
            async def remote(_key, control):
                ledger = json.loads(Path(directory, "hive-request-ledger.json").read_text())
                self.assertEqual(ledger["image_requests_reserved"], 2)
                self.assertEqual(ledger["audio_seconds_reserved"], 0)
                self.assertEqual(ledger["requests_started"], len(results) + 1)
                self.assertTrue(Path(directory, "controls.json").exists())
                results.append(control["case"])
                return {"case": control["case"], "available": True, "status": "success",
                        "http_status": 200, "ai_generated_score": .9, "deepfake_score": .1, "duration_ms": 1}

            with patch.object(probe, "dotenv_values", return_value={"HIVE_V3_API_KEY": "secret-not-for-output",
                    "DATABASE_URL": "private-db-not-for-output", "GEMINI_API_KEY": "unrelated-not-for-output"}) as config, \
                 patch.object(probe, "probe_once", new=AsyncMock(side_effect=remote)) as calls:
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    record = await probe.main(self.args(directory))
            config.assert_called_once_with("/not-read/private.env", interpolate=False)
            self.assertEqual(calls.await_count, 2)
            self.assertEqual(results, [control["case"] for control in probe.CONTROLS])
            self.assertEqual(record["request_accounting"]["nominal_price_ceiling_usd"], .012)
            self.assertEqual(record["request_accounting"]["requests_started"], 2)
            self.assertIn("not UI", record["scope"])
            self.assertEqual(dict(os.environ), environment_before)
            combined = stdout.getvalue() + Path(directory, "controls.json").read_text() + Path(directory, "hive-request-ledger.json").read_text()
            for private in ("secret-not-for-output", "private-db-not-for-output", "unrelated-not-for-output", "/not-read/private.env"):
                self.assertNotIn(private, combined)

    async def test_missing_key_refuses_all_requests(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values", return_value={}), \
             patch.object(probe, "probe_once", new=AsyncMock()) as remote:
            with self.assertRaises(ValueError):
                await probe.main(self.args(directory))
            self.assertFalse(Path(directory, "hive-request-ledger.json").exists())
        remote.assert_not_called()

    async def test_legacy_named_key_fallback_only_sends_reviewed_v3_controls(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "dotenv_values", return_value={"HIVE_API_KEY": "test-v3-secret"}), \
             patch.object(probe, "probe_once", new=AsyncMock(return_value={"available": False, "status": "timeout"})) as remote:
            with contextlib.redirect_stdout(io.StringIO()):
                await probe.main(self.args(directory))
            self.assertEqual(remote.await_count, 2)
            self.assertTrue(all(item.args[0] == "test-v3-secret" for item in remote.await_args_list))

    async def test_direct_unreviewed_control_never_starts_http(self):
        with patch.object(probe.httpx, "AsyncClient") as remote:
            with self.assertRaises(ValueError):
                await probe.probe_once("test-secret", {"case": "nasa_source_photo", "data": b"arbitrary"})
        remote.assert_not_called()

    async def test_single_fixed_https_request_parser_no_raw_output(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"model": "hive/ai-generated-and-deepfake-content-detection", "version": "private-version",
                "id": "private-job", "output": [{"classes": [{"class": "ai_generated", "value": .9},
                    {"class": "deepfake", "value": .01}, {"class": "private-metadata", "value": .4}]}]}, request=request)
        def factory(**kwargs):
            self.assertFalse(kwargs["trust_env"])
            self.assertFalse(kwargs["follow_redirects"])
            return CLIENT(transport=httpx.MockTransport(handler), **kwargs)
        with patch.object(probe.httpx, "AsyncClient", side_effect=factory):
            result = await probe.probe_once("test-secret", probe.load_controls()[0])
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), probe.HIVE_V3_API_URL)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].headers["Authorization"], "Bearer test-secret")
        self.assertTrue(result["available"])
        self.assertEqual(result["ai_generated_score"], .9)
        for private in ("private-job", "private-version", "private-metadata", "test-secret"):
            self.assertNotIn(private, json.dumps(result))

    async def test_timeout_and_http_errors_do_not_retry_or_echo_details(self):
        for status in (202, 401, 402, 429, 500, None):
            attempts = []
            def handler(request):
                attempts.append(1)
                if status is None:
                    raise httpx.ReadTimeout("secret-debug", request=request)
                return httpx.Response(status, json={"message": "secret-debug", "id": "private-job"}, request=request)
            with self.subTest(status=status), patch.object(probe.httpx, "AsyncClient", side_effect=lambda **kwargs:
                    CLIENT(transport=httpx.MockTransport(handler), **kwargs)):
                result = await probe.probe_once("test-secret", probe.load_controls()[0])
            self.assertEqual(len(attempts), 1)
            self.assertFalse(result["available"])
            self.assertNotIn("secret-debug", json.dumps(result))

    async def test_oversized_response_is_bounded_and_not_retried(self):
        attempts = []
        def handler(request):
            attempts.append(1)
            return httpx.Response(200, content=b"x" * (probe.MAX_RESPONSE_BYTES + 1), request=request)
        with patch.object(probe.httpx, "AsyncClient", side_effect=lambda **kwargs:
                CLIENT(transport=httpx.MockTransport(handler), **kwargs)):
            result = await probe.probe_once("test-secret", probe.load_controls()[1])
        self.assertEqual(result["status"], "response_size_limit")
        self.assertEqual(len(attempts), 1)

    def test_untrusted_status_or_scores_are_not_echoed(self):
        result = probe.summarize({"status": "private-status", "available": False,
            "ai_generated_score": "private-value", "deepfake_score": float("nan"), "raw": {"id": "private-id"}})
        self.assertEqual(result["status"], "invalid_response")
        self.assertIsNone(result["ai_generated_score"])
        self.assertIsNone(result["deepfake_score"])
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
