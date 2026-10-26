"""Complete Gemini output and model-compatible REST payloads, without APIs."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core import gemini_client as gemini
from app.services.provider_diagnostics import provider_failure_metadata


def envelope():
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"ok":true}'}]}}]}


class GeminiResponseValidationTests(unittest.TestCase):
    def reject(self, body, issue):
        with self.assertRaises(gemini.GeminiError) as raised:
            gemini._complete_response(body, "unit-model")
        self.assertEqual(raised.exception.status, "invalid_response")
        self.assertEqual(provider_failure_metadata(raised.exception), {"response_issue": issue})
        self.assertNotIn("private-control", str(raised.exception))

    def test_stop_preserves_visible_parts_without_including_thoughts(self):
        body = envelope()
        body["candidates"][0]["content"]["parts"] = [
            {"thought": True, "text": "private-control"},
            {"text": '{"value":1'}, {"text": "6}"}]
        result = gemini._complete_response(body, "unit-model")
        self.assertEqual(result, '{"value":16}')
        self.assertEqual(result.model_name, "unit-model")
        self.assertNotIn("private-control", result)

    def test_missing_stop_cannot_certify_json_looking_text_as_complete(self):
        for finish in (None, "", "OTHER", "FINISH_REASON_UNSPECIFIED", "CONTINUATION", "private-control", [], True):
            body = envelope()
            body["candidates"][0]["finishReason"] = finish
            with self.subTest(finish=finish):
                self.reject(body, "unexpected_finish")
        body = envelope()
        del body["candidates"][0]["finishReason"]
        self.reject(body, "unexpected_finish")

    def test_max_tokens_discards_even_complete_looking_json_and_does_not_use_thought(self):
        body = envelope()
        body["candidates"][0]["finishReason"] = "MAX_TOKENS"
        body["candidates"][0]["content"]["parts"].insert(0, {"thought": True, "text": "private-control"})
        self.reject(body, "token_limit")

    def test_explicit_content_stops_have_distinct_non_recoverable_diagnostic(self):
        for finish in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII",
                       "IMAGE_SAFETY", "ESCALATION", "PUP_LIMITED_DISABLED"):
            body = envelope()
            body["candidates"][0].update(finishReason=finish, finishMessage="private-control")
            with self.subTest(finish=finish):
                self.reject(body, "content_blocked")

    def test_prompt_block_overrides_even_inconsistent_complete_candidate(self):
        for block in ("SAFETY", "BLOCKLIST", "OTHER", "private-control"):
            body = envelope()
            body["promptFeedback"] = {"blockReason": block, "blockReasonMessage": "private-control"}
            self.reject(body, "content_blocked")
        body["promptFeedback"] = {"blockReason": "BLOCK_REASON_UNSPECIFIED"}
        self.assertEqual(gemini._complete_response(body, "unit-model"), '{"ok":true}')

    def test_explicit_blocked_rating_prevents_acceptance_of_inconsistent_stop(self):
        body = envelope()
        body["candidates"][0]["safetyRatings"] = [{"blocked": True, "category": "private-control"}]
        self.reject(body, "content_blocked")

    def test_error_envelope_never_accepts_complete_looking_candidate(self):
        body = envelope()
        body["error"] = {"code": 503, "message": "private-control"}
        self.reject(body, "malformed_envelope")

    def test_malformed_safety_ratings_do_not_disappear_during_validation(self):
        for ratings in (None, {}, "private-control", [None], [True]):
            body = envelope()
            body["candidates"][0]["safetyRatings"] = ratings
            self.reject(body, "malformed_envelope")

    def test_malformed_envelopes_and_part_types_have_safe_diagnostic(self):
        malformed = (None, [], {}, {"candidates": {}}, {"candidates": [None]},
                     {"candidates": [{"finishReason": "STOP"}]},
                     {"candidates": [{"finishReason": "STOP", "content": {"parts": None}}]},
                     {"candidates": [{"finishReason": "STOP", "content": {"parts": [False]}}]},
                     {**envelope(), "promptFeedback": "private-control"},
                     {**envelope(), "promptFeedback": {"blockReason": True}})
        for body in malformed:
            self.reject(body, "malformed_envelope")

    def test_empty_or_thought_only_output_is_not_a_visible_response(self):
        for parts in ([], [{"text": " \n\t"}], [{"thought": True, "text": "private-control"}],
                      [{"inlineData": {"data": "private-control"}}]):
            body = envelope()
            body["candidates"][0]["content"]["parts"] = parts
            self.reject(body, "empty_content")
        self.reject({"candidates": []}, "empty_content")

    def test_invalid_text_or_thought_type_never_coerces_private_objects(self):
        for part in ({"text": 42}, {"text": {"private-control": True}},
                     {"text": "private-control", "thought": "false"}):
            body = envelope()
            body["candidates"][0]["content"]["parts"] = [part]
            self.reject(body, "invalid_content")

    def test_response_length_guard_still_applies(self):
        body = envelope()
        body["candidates"][0]["content"]["parts"] = [{"text": "x" * 30001}]
        self.reject(body, "content_limit")


class GeminiRequestCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control", "GEMINI_FALLBACK_MODELS": "",
            "GEMINI_MODEL_NAME": "gemini-3.1-flash-lite", "GEMINI_LOCAL_ADMISSION_ENABLED": "false"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.sent = []
        self.client_type = httpx.AsyncClient

    def client(self, *, fail_first=False, response=None):
        def respond(request):
            self.sent.append({"path": request.url.path, "body": json.loads(request.content)})
            if fail_first and len(self.sent) == 1:
                return httpx.Response(503)
            return response if response is not None else httpx.Response(200, json=envelope())
        return lambda **kwargs: self.client_type(transport=httpx.MockTransport(respond), **kwargs)

    async def test_gemini3_and_later_use_default_sampling_preserving_schema_and_output_cap(self):
        for model in ("gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-4-test"):
            self.sent.clear()
            with self.subTest(model=model), patch.object(gemini, "_reserve_request", new=AsyncMock()) as reserve, \
                 patch("httpx.AsyncClient", side_effect=self.client()):
                result = await gemini.generate_text("fixed control", model_name=model, temperature=0,
                    max_tokens=9999, response_schema={"type": "OBJECT"})
            self.assertEqual(result, '{"ok":true}')
            config = self.sent[0]["body"]["generationConfig"]
            self.assertNotIn("temperature", config)
            self.assertEqual(config["maxOutputTokens"], 4096)
            self.assertEqual(config["responseSchema"], {"type": "OBJECT"})
            reserve.assert_awaited_once_with(model)

    async def test_legacy_sampling_is_preserved_per_explicit_model_fallback(self):
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "gemini-2.5-flash"}), \
             patch.object(gemini, "_reserve_request", new=AsyncMock()) as reserve, \
             patch("httpx.AsyncClient", side_effect=self.client(fail_first=True)):
            result = await gemini.generate_text("fixed control", temperature=.1)
        self.assertEqual(result.model_name, "gemini-2.5-flash")
        self.assertEqual(len(self.sent), 2)
        self.assertNotIn("temperature", self.sent[0]["body"]["generationConfig"])
        self.assertNotIn("thinkingConfig", self.sent[1]["body"]["generationConfig"])
        self.assertEqual(self.sent[1]["body"]["generationConfig"]["temperature"], .1)
        self.assertEqual(reserve.await_count, 2)

    async def test_omitted_sampling_does_not_silently_accept_invalid_caller_configuration(self):
        for temperature in (True, None, "0", -1, 3, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(temperature=temperature), \
                 patch.object(gemini, "_reserve_request", new=AsyncMock()) as reserve, \
                 patch("httpx.AsyncClient") as client:
                with self.assertRaises(gemini.GeminiError) as raised:
                    await gemini.generate_text("fixed control", temperature=temperature)
            self.assertEqual(raised.exception.status, "invalid_configuration")
            client.assert_not_called()
            reserve.assert_not_awaited()

    async def test_core_partial_never_rotates_models_or_returns_partial_evidence(self):
        body = envelope()
        body["candidates"][0]["finishReason"] = "MAX_TOKENS"
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "gemini-2.5-flash"}), \
             patch.object(gemini, "_reserve_request", new=AsyncMock()) as reserve, \
             patch("httpx.AsyncClient", side_effect=self.client(response=httpx.Response(200, json=body))):
            with self.assertRaises(gemini.GeminiError) as raised:
                await gemini.generate_text("fixed control")
        self.assertEqual(provider_failure_metadata(raised.exception), {"response_issue": "token_limit"})
        reserve.assert_awaited_once()
        self.assertEqual(len(self.sent), 1)

    async def test_json_decode_failure_does_not_expose_body_or_headers(self):
        response = httpx.Response(200, content=b"private-control", headers={"x-private": "private-control"})
        with patch.object(gemini, "_reserve_request", new=AsyncMock()), \
             patch("httpx.AsyncClient", side_effect=self.client(response=response)):
            with self.assertRaises(gemini.GeminiError) as raised:
                await gemini.generate_text("fixed control")
        self.assertEqual(provider_failure_metadata(raised.exception), {"response_issue": "malformed_envelope"})
        self.assertNotIn("private-control", str(raised.exception))
