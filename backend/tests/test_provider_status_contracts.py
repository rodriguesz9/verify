"""Offline status/role diagnostics, never provider correctness or paid calls."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from app.core.gemini_analyzer import analyze_image_with_vision
from app.core.sightengine_client import check_deepfake
from app.services.capabilities import capability_report
from app.services.evidence_policy import media_report
from app.services.hive_service import HiveV3Budget, check_hive_media


HTTP_FAILURES = {401: "invalid_credentials", 403: "access_denied", 402: "quota_exhausted",
                 429: "rate_limited", 503: "unavailable", 500: "error"}


class ProviderStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_sightengine_missing_keys_are_configuration_not_transport_failure(self):
        with patch("app.core.sightengine_client.SIGHTENGINE_API_USER", ""), \
                patch("app.core.sightengine_client.SIGHTENGINE_API_SECRET", ""), \
                patch("httpx.AsyncClient.post", new=AsyncMock()) as remote:
            result = await check_deepfake(helpers.valid_png())
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(result["available"])
        self.assertEqual(media_report({"sightengine": result})["provider_coverage"]["sightengine"]["status"], "not_configured")
        remote.assert_not_awaited()

    async def test_sightengine_http_failures_are_explicit_without_retry_or_error_body(self):
        for code, status in HTTP_FAILURES.items():
            response = httpx.Response(code, json={"error": "private-marker"},
                request=httpx.Request("POST", "https://api.sightengine.com/1.0/check.json"))
            with self.subTest(code=code), patch("app.core.sightengine_client.SIGHTENGINE_API_USER", "unit-only"), \
                    patch("app.core.sightengine_client.SIGHTENGINE_API_SECRET", "unit-only"), \
                    patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as remote:
                result = await check_deepfake(helpers.valid_png())
            self.assertEqual(result["status"], status)
            self.assertFalse(result["available"])
            self.assertNotIn("private-marker", json.dumps(result))
            self.assertEqual(remote.await_count, 1)

    async def test_sightengine_timeout_is_not_unspecified_error(self):
        with patch("app.core.sightengine_client.SIGHTENGINE_API_USER", "unit-only"), \
                patch("app.core.sightengine_client.SIGHTENGINE_API_SECRET", "unit-only"), \
                patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ReadTimeout("private-marker"))) as remote:
            result = await check_deepfake(helpers.valid_png())
        self.assertEqual(result["status"], "timeout")
        self.assertNotIn("private-marker", json.dumps(result))
        self.assertEqual(remote.await_count, 1)

    async def test_gemini_vision_missing_key_never_calls_provider_or_votes(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), \
                patch("app.core.gemini_analyzer.generate_text", new=AsyncMock()) as remote:
            result = await analyze_image_with_vision(helpers.valid_png(), "image/png", {})
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(result["available"])
        self.assertFalse(result["voting_eligible"])
        self.assertIsNone(result["visual_score"])
        remote.assert_not_awaited()

    async def test_hive_http_failure_taxonomy_keeps_reserved_budget(self):
        for code, status in HTTP_FAILURES.items():
            with self.subTest(code=code), patch.dict(os.environ, {
                    "HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "unit-only", "HIVE_V3_MEDIA_TYPES": "image",
                    "HIVE_V3_IMAGE_REQUEST_LIMIT": "1"}), \
                    patch("app.services.hive_service.hive_v3_budget", HiveV3Budget()), \
                    patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(code,
                        json={"error": "private-marker"}))) as remote:
                result = await check_hive_media(helpers.valid_png())
                blocked = await check_hive_media(helpers.valid_png())
            self.assertEqual(result["status"], status)
            self.assertFalse(result["available"])
            self.assertEqual(blocked["status"], "budget_exhausted")
            self.assertNotIn("private-marker", json.dumps(result))
            self.assertEqual(remote.await_count, 1)

    async def test_hive_timeout_explicit_no_refund_or_retransmission(self):
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "unit-only",
                    "HIVE_V3_MEDIA_TYPES": "image", "HIVE_V3_IMAGE_REQUEST_LIMIT": "1"}), \
                patch("app.services.hive_service.hive_v3_budget", HiveV3Budget()), \
                patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ReadTimeout("private-marker"))) as remote:
            result = await check_hive_media(helpers.valid_png())
            blocked = await check_hive_media(helpers.valid_png())
        self.assertEqual(result["status"], "timeout")
        self.assertFalse(result["available"])
        self.assertEqual(blocked["status"], "budget_exhausted")
        self.assertNotIn("private-marker", json.dumps(result))
        self.assertEqual(remote.await_count, 1)


class CapabilityRoleTests(unittest.TestCase):
    def test_current_roles_describe_source_comparison_without_health_claim(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "private-marker", "OPENROUTER_API_KEY": "private-marker",
                    "SERPERAPI_KEY": "private-marker", "SOURCE_CROSSCHECK_ENABLED": "true"}), \
                patch("httpx.AsyncClient.send", new=AsyncMock()) as remote:
            result = capability_report()
        self.assertEqual(result["truth_decision_paths"], ["published_claim_reviews", "retrieved_source_bodies"])
        self.assertEqual(result["truth_policy"], "published_claim_reviews_or_grounded_source_comparison")
        self.assertTrue(result["source_crosscheck"]["enabled"])
        self.assertFalse(result["source_crosscheck"]["model_agreement_is_evidence"])
        for name in ("gemini", "openrouter"):
            self.assertIn("grounded_comparison_assistant", result["providers"][name]["roles"])
            self.assertEqual(result["providers"][name]["operational_status"], "not_tested")
        self.assertFalse(result["providers"]["serper"]["search_snippets_are_decisive_evidence"])
        self.assertNotIn("private-marker", json.dumps(result))
        remote.assert_not_awaited()

    def test_disabled_source_crosscheck_remains_explicit(self):
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "false"}):
            result = capability_report()
        self.assertFalse(result["source_crosscheck"]["enabled"])
        self.assertEqual(result["source_crosscheck"]["operational_status"], "not_tested")
