"""Observable auxiliary-provider states; no real requests or precision claims."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers  # disables real provider credentials before application imports
import httpx
from app.core.gemini_analyzer import analyze_image_with_vision, VISION_SCHEMA
from app.core.gemini_client import GeneratedText, GeminiError
from app.services.evidence_policy import media_report
from app.services.reverse_search_service import check_tineye_reverse_search, check_wayback_machine


def visual_control(**overrides):
    return {"visual_forensics_verdict": "Suspicious", "visual_score": 50,
            "anatomical_issues": [], "physical_consistency_issues": [],
            "editing_software_hints": [], "ai_model_hints": [],
            "compression_artifacts_detected": False, "ai_generation_artifacts_detected": False,
            "conventional_editing_detected": False, "pixel_level_summary": "Observações auxiliares de controle.",
            "plain_explanation": "Não determina origem, identidade ou verdade.",
            "elderly_tip": "Confirme com a fonte original.", **overrides}


class VisionResponseStateTests(unittest.IsolatedAsyncioTestCase):
    async def _analyze(self, data):
        response = GeneratedText(json.dumps(data)); response.model_name = "test-model"
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-key"}), \
             patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(return_value=response)) as call:
            result = await analyze_image_with_vision(b"fixture-bytes", "image/png", {})
        return result, call

    async def test_complete_response_is_structured_bounded_non_voting_inspection(self):
        result, call = await self._analyze(visual_control(anatomical_issues=["  Observação auxiliar  "],
                                                       visual_forensics_verdict="AI_Generated", visual_score=0))
        self.assertTrue(result["available"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["anatomical_issues"], ["Observação auxiliar"])
        self.assertEqual(result["visual_score"], 0)
        self.assertEqual(result["decision_role"], "inspection_only")
        self.assertFalse(result["voting_eligible"])
        self.assertEqual(call.call_args.kwargs["response_schema"], VISION_SCHEMA)
        self.assertEqual(len(VISION_SCHEMA["required"]), 12)
        self.assertEqual(media_report({"gemini_vision": result})["analysis_status"], "inconclusive")
        json.dumps(result, allow_nan=False)

    async def test_empty_partial_non_object_and_missing_fields_are_invalid_not_success(self):
        values = [{}, [], None, {"visual_forensics_verdict": "Authentic", "visual_score": 100}]
        for field in VISION_SCHEMA["required"]:
            partial = visual_control()
            partial.pop(field)
            values.append(partial)
        for data in values:
            with self.subTest(data=data):
                result, _ = await self._analyze(data)
                self.assertFalse(result["available"])
                self.assertEqual(result["status"], "invalid_response")
                self.assertIsNone(result["visual_score"])
                self.assertFalse(result["voting_eligible"])

    async def test_invalid_categories_and_nonfinite_coerced_scores_rejected(self):
        values = [visual_control(visual_forensics_verdict="Certificado autêntico"),
                  visual_control(visual_forensics_verdict=[])]
        values += [visual_control(visual_score=score) for score in (True, "90", None, -1, 101, float("nan"), float("inf"), 10 ** 500)]
        for data in values:
            with self.subTest(data=data):
                result, _ = await self._analyze(data)
                self.assertFalse(result["available"])
                self.assertEqual(result["status"], "invalid_response")

    async def test_wrong_booleans_lists_texts_and_oversized_values_rejected(self):
        values = [visual_control(compression_artifacts_detected=1), visual_control(ai_generation_artifacts_detected="false"),
                  visual_control(anatomical_issues="none"), visual_control(anatomical_issues=[True]),
                  visual_control(ai_model_hints=["" ]), visual_control(editing_software_hints=["x"] * 21),
                  visual_control(physical_consistency_issues=["x" * 501]), visual_control(pixel_level_summary=None),
                  visual_control(plain_explanation="  "), visual_control(pixel_level_summary="x" * 3001),
                  visual_control(elderly_tip="x" * 1001)]
        for data in values:
            with self.subTest(data=data):
                result, _ = await self._analyze(data)
                self.assertEqual(result["status"], "invalid_response")
                self.assertFalse(result["available"])

    async def test_undeclared_fields_cannot_override_policy_source_or_precision(self):
        result, _ = await self._analyze(visual_control(available=True, status="success", voting_eligible=True,
                                                     confidence=100, invented_sources=["private-fixture"],
                                                     decision_role="truth_detector", veracity_status="supported"))
        self.assertTrue(result["available"])
        self.assertFalse(result["voting_eligible"])
        self.assertEqual(result["decision_role"], "inspection_only")
        for field in ("confidence", "invented_sources", "veracity_status"):
            self.assertNotIn(field, result)
        self.assertEqual(media_report({"gemini_vision": result})["veracity_status"], "unverified")

    async def test_provider_failure_status_preserved_without_raw_exception_leak(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-key"}), \
             patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(side_effect=GeminiError("Gemini indisponível (HTTP 429).", "rate_limited", 429))):
            result = await analyze_image_with_vision(b"fixture-bytes", "image/png", {})
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "rate_limited")
        self.assertFalse(result["voting_eligible"])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-key"}), \
             patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(side_effect=RuntimeError("private-fixture-token"))):
            result = await analyze_image_with_vision(b"fixture-bytes", "image/png", {})
        self.assertNotIn("private-fixture-token", str(result))


class TinEyeResponseStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_absent_key_is_skipped_without_false_zero_or_network(self):
        with patch.dict(os.environ, {"TINEYE_API_KEY": ""}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            result = await check_tineye_reverse_search(b"fixture")
        self.assertFalse(result["available"])
        self.assertIsNone(result["matches_count"])
        post.assert_not_awaited()

    async def test_successful_empty_result_preserves_real_zero(self):
        with patch.dict(os.environ, {"TINEYE_API_KEY": "offline-key"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json={"results": {"matches": []}}))):
            result = await check_tineye_reverse_search(b"fixture")
        self.assertTrue(result["available"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["matches_count"], 0)

    async def test_successful_matches_keep_count_and_bounded_preview(self):
        matches = [{"image_url": f"https://example.test/control-{index}.jpg"} for index in range(5)]
        with patch.dict(os.environ, {"TINEYE_API_KEY": "offline-key"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json={"results": {"matches": matches}}))):
            result = await check_tineye_reverse_search(b"fixture")
        self.assertTrue(result["available"])
        self.assertEqual(result["matches_count"], 5)
        self.assertEqual(len(result["top_matches"]), 3)

    async def test_http_errors_and_transport_failures_are_unavailable_unknown_count(self):
        for code, status in ((401, "invalid_credentials"), (403, "access_denied"), (402, "quota_exhausted"), (429, "rate_limited"), (500, "error")):
            with self.subTest(code=code), patch.dict(os.environ, {"TINEYE_API_KEY": "offline-key"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(code, json={"private-error": "do-not-print"}))):
                result = await check_tineye_reverse_search(b"fixture")
                self.assertFalse(result["available"])
                self.assertEqual(result["status"], status)
                self.assertIsNone(result["matches_count"])
                self.assertNotIn("do-not-print", str(result))
        with patch.dict(os.environ, {"TINEYE_API_KEY": "offline-key"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("private-fixture-token"))):
            result = await check_tineye_reverse_search(b"fixture")
        self.assertFalse(result["available"])
        self.assertIsNone(result["matches_count"])
        self.assertNotIn("private-fixture-token", str(result))

    async def test_malformed_success_payload_is_not_zero_matches(self):
        for body in ({}, [], {"results": {}}, {"results": {"matches": "unknown"}}, {"results": {"matches": [None]}}):
            with self.subTest(body=body), patch.dict(os.environ, {"TINEYE_API_KEY": "offline-key"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=body))):
                result = await check_tineye_reverse_search(b"fixture")
                self.assertFalse(result["available"])
                self.assertEqual(result["status"], "invalid_response")
                self.assertIsNone(result["matches_count"])


class WaybackResponseStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_does_not_query_private_url(self):
        with patch.dict(os.environ, {"WAYBACK_API_ENABLED": "false"}), patch("httpx.AsyncClient.get", new=AsyncMock()) as get:
            result = await check_wayback_machine("https://example.test/private?token=private-fixture-token")
        self.assertFalse(result["checked"])
        self.assertEqual(result["status"], "disabled")
        get.assert_not_awaited()

    async def test_successful_no_result_is_distinct_from_service_failure(self):
        with patch.dict(os.environ, {"WAYBACK_API_ENABLED": "true"}):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, json={"archived_snapshots": {}}))):
                empty = await check_wayback_machine("https://example.test/control")
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(503, json={"private-error": "do-not-print"}))):
                failed = await check_wayback_machine("https://example.test/control")
        self.assertTrue(empty["checked"])
        self.assertEqual(empty["status"], "no_results")
        self.assertFalse(failed["checked"])
        self.assertEqual(failed["status"], "error")
        self.assertNotIn("do-not-print", str(failed))

    async def test_transport_and_json_errors_never_echo_sensitive_query(self):
        secret = "private-fixture-token"
        url = f"https://example.test/private?token={secret}"
        with patch.dict(os.environ, {"WAYBACK_API_ENABLED": "true"}):
            with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.ConnectError(url))):
                result = await check_wayback_machine(url)
            self.assertFalse(result["checked"])
            self.assertNotIn(secret, str(result))
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text="not-json"))):
                result = await check_wayback_machine(url)
            self.assertFalse(result["checked"])
            self.assertNotIn(secret, str(result))


if __name__ == "__main__":
    unittest.main()
