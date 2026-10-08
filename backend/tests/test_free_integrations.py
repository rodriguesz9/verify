import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from helpers import valid_png, valid_wav
from app.core import openrouter_service as router
from app.core.pipeline import run_pipeline
from app.core.serper_client import search_news
from app.services.audio_service import transcribe_with_assemblyai
from app.services.hive_service import HIVE_V3_MODEL, check_hive_media, parse_hive_v3_scores
from app.services.media_analysis import image_layers
from app.core.gemini_client import GeminiError, generate_text
from app.services.evidence_policy import media_report


def router_response(value='{"claims": []}', **extra):
    return {"model": "vendor/model:free", "choices": [{"finish_reason": "stop", "message": {"content": value}}],
            "usage": {"cost": 0}, **extra}


def hive_v3(classes):
    return {"model": HIVE_V3_MODEL, "version": "1", "output": [{"classes": classes}]}


class FreeRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "unit-test-not-secret", "OPENROUTER_MODEL": "openrouter/free",
            "OPENROUTER_FALLBACK_MODELS": "", "OPENROUTER_ENABLED": "true", "OPENROUTER_DAILY_LIMIT": "40"})
        self.env.start()
        router._budget_day, router._budget_count, router._minute_requests, router._cooldown_until = "", 0, [], 0

    def tearDown(self):
        self.env.stop()
        router._budget_day, router._budget_count, router._minute_requests, router._cooldown_until = "", 0, [], 0

    async def test_paid_models_and_fake_free_router_blocked_before_http(self):
        for model in ("openrouter/auto:free", "openrouter/auto", "google/paid", "https://evil.test/free", "x/y:free:other"):
            with self.subTest(model=model), patch.dict(os.environ, {"OPENROUTER_MODEL": model}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
                result = await router.analyze_with_openrouter("Uma afirmação suficientemente longa.")
                self.assertEqual(result["status"], "invalid_configuration")
                post.assert_not_awaited()

    async def test_paid_unused_fallback_is_also_rejected(self):
        with patch.dict(os.environ, {"OPENROUTER_FALLBACK_MODELS": "x/y:free,z/paid"}), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            with self.assertRaises(router.OpenRouterError):
                await router.generate("texto")
            post.assert_not_awaited()

    async def test_free_payload_and_actual_model_recorded(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response()))) as post:
            result = await router.analyze_with_openrouter("O Brasil está na América do Sul.")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "openrouter/free")
        self.assertTrue(all(value == 0 for value in post.call_args.kwargs["json"]["provider"]["max_price"].values()))
        self.assertEqual(post.call_args.kwargs["json"]["provider"]["sort"], "latency")
        self.assertTrue(post.call_args.kwargs["json"]["provider"]["require_parameters"])
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], router.CLAIMS_FORMAT)
        self.assertEqual(result["model_used"], "vendor/model:free")
        self.assertEqual(result["decision_role"], "search_hints_only")
        self.assertNotIn("verdict", result)

    async def test_invented_claims_and_scores_are_discarded(self):
        text = "Não haverá imposto em 2026."
        value = json.dumps({"claims": [text, "Haverá imposto em 2026.", text, None], "verdict": "Authentic", "score": 100})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response(value)))):
            result = await router.analyze_with_openrouter(text)
        self.assertEqual(result["claims"], [text])
        self.assertNotIn("score", result)

    async def test_single_complete_json_fence_is_accepted_without_repair_call(self):
        text = "O Brasil está na América do Sul."
        body = "```json\n" + json.dumps({"claims": [text]}) + "\n```"
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response(body)))) as post:
            result = await router.analyze_with_openrouter(text)
        self.assertTrue(result["available"])
        self.assertEqual(result["claims"], [text])
        self.assertEqual(post.await_count, 1)

    async def test_ambiguous_prose_or_multiple_json_objects_are_rejected(self):
        for value in ('Aqui está: {"claims": []}', '{"claims": []}{"claims": []}', '```python\n{"claims": []}\n```'):
            with self.subTest(value=value), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response(value)))):
                result = await router.analyze_with_openrouter("Uma afirmação literal de controle.")
                self.assertFalse(result["available"])
                self.assertEqual(result["response_issue"], "invalid_json")
                self.assertEqual(result["model_used"], "vendor/model:free")

    async def test_invalid_and_truncated_responses_are_not_success(self):
        for body in ([], {"choices": []}, router_response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
                     router_response(usage=[]), router_response(usage={"cost": .01}), router_response(usage={"cost": True}),
                     router_response("not json"), router_response('{"claims": "wrong"}')):
            with self.subTest(body=body), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=body))):
                result = await router.analyze_with_openrouter("Uma alegação literal longa.")
                self.assertFalse(result["available"])

    async def test_truncation_reason_and_empty_ocr_are_explicit_without_retry(self):
        body = router_response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}])
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=body))) as post:
            result = await router.analyze_with_openrouter("Uma alegação literal de controle.")
        self.assertIn("limite de tokens", result["reason"])
        self.assertEqual(post.await_count, 1)
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response('{"text":""}')))):
            result = await router.extract_image_text(valid_png(), "image/png")
        self.assertTrue(result["available"])
        self.assertEqual(result["status"], "no_text")
        self.assertEqual(result["text"], "")
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(429))) as post:
            result = await router.extract_image_text(valid_png(), "image/png")
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["status"], "rate_limited")
        self.assertEqual(post.await_count, 1)

    async def test_quota_pause_and_no_paid_fallback_or_retry(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(429, json={"error": "private-secret"}))) as post:
            first = await router.analyze_with_openrouter("Uma alegação longa.")
            second = await router.analyze_with_openrouter("Uma alegação longa.")
        self.assertEqual(first["status"], "rate_limited")
        self.assertEqual(second["status"], "rate_limited")
        self.assertEqual(post.await_count, 1)
        self.assertNotIn("private-secret", str(first))

    async def test_local_daily_limit_includes_failed_attempts(self):
        with patch.dict(os.environ, {"OPENROUTER_DAILY_LIMIT": "1"}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(500))) as post:
            await router.analyze_with_openrouter("Uma alegação longa.")
            self.assertEqual((await router.analyze_with_openrouter("Uma alegação longa."))["status"], "rate_limited")
            self.assertEqual(post.await_count, 1)

    async def test_only_free_fallback_after_unavailable_model(self):
        with patch.dict(os.environ, {"OPENROUTER_FALLBACK_MODELS": "vendor/model:free"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=[httpx.Response(503), httpx.Response(200, json=router_response())])) as post:
            self.assertTrue((await router.analyze_with_openrouter("Uma alegação longa."))["available"])
        self.assertEqual([call.kwargs["json"]["model"] for call in post.call_args_list], ["openrouter/free", "vendor/model:free"])

    async def test_auxiliary_model_cannot_make_unverified_claim_true(self):
        with patch("app.core.pipeline.analyze_with_openrouter", new=AsyncMock(return_value={"available": True, "status": "success",
                 "claims": ["O Brasil está na América do Sul."], "verdict": "Authentic", "score": 100, "decision_role": "search_hints_only"})), \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])), \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])):
            result = await run_pipeline("O Brasil está na América do Sul.")
        self.assertEqual(result["report"]["analysis_status"], "inconclusive")
        self.assertEqual(result["report"]["veracity_status"], "unverified")

    async def test_media_text_retrieval_does_not_wait_or_spend_on_second_extraction(self):
        from app.services.media_analysis import check_content
        with patch("app.core.pipeline.analyze_with_openrouter", new=AsyncMock()) as ai, \
             patch("app.core.pipeline.extract_claims_with_ai", new=AsyncMock()) as gemini, \
             patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=[])) as facts, \
             patch("app.core.pipeline.search_news", new=AsyncMock(return_value=[])):
            report = await check_content("O Brasil está na América do Sul.", "ocr")
        ai.assert_not_awaited()
        gemini.assert_not_awaited()
        self.assertEqual(facts.call_args_list[0].args[0], "O Brasil está na América do Sul.")
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertNotIn("openrouter", report["provider_coverage"])

    async def test_free_vision_ocr_sends_real_bytes_not_filename(self):
        import base64
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response('{"text":"Pague uma taxa"}')))) as post:
            result = await router.extract_image_text(valid_png(), "image/png")
        content = post.call_args.kwargs["json"]["messages"][-1]["content"]
        uri = content[1]["image_url"]["url"]
        self.assertEqual(base64.b64decode(uri.split(",", 1)[1]), valid_png())
        self.assertEqual(result["decision_role"], "ocr_only")
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], router.OCR_FORMAT)
        self.assertEqual(result["text"], "Pague uma taxa")
        self.assertNotIn("verdict", result)

    async def test_missing_gemini_uses_free_ocr_fallback(self):
        from app.core.gemini_analyzer import extract_text_from_image
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response('{"text":"Olá"}')))):
            result = await extract_text_from_image(valid_png(), "image/png")
        self.assertEqual(result["provider"], "openrouter")

    async def test_gemini_failure_uses_free_ocr_without_leaking_error(self):
        from app.core.gemini_analyzer import extract_text_from_image
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unit-test"}), \
             patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(side_effect=RuntimeError("private-secret"))), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=router_response('{"text":"Olá"}')))):
            result = await extract_text_from_image(valid_png(), "image/png")
        self.assertEqual(result["fallback_from"], "gemini_unavailable")
        self.assertNotIn("private-secret", str(result))


class HiveV3Tests(unittest.IsolatedAsyncioTestCase):
    def test_distinct_audio_head_and_negative_classes(self):
        data = hive_v3([{"class": "not_ai_generated", "value": .99}, {"class": "ai_generated", "value": .01},
                        {"class": "deepfake", "value": .98}, {"class": "ai_generated_audio", "value": .8}])
        self.assertEqual(parse_hive_v3_scores(data)["ai_generated_score"], .01)
        self.assertEqual(parse_hive_v3_scores(data)["deepfake_score"], .98)
        self.assertEqual(parse_hive_v3_scores(data, "audio")["ai_generated_score"], .8)
        self.assertIsNone(parse_hive_v3_scores(data, "audio")["deepfake_score"])
        self.assertFalse(parse_hive_v3_scores(hive_v3([{"class": "ai_generated", "value": .99}]), "audio")["available"])

    def test_v2_format_wrong_model_invalid_values_never_success(self):
        for data in ({}, {"model": "wrong", "output": []}, hive_v3([{"class": "not_ai_generated", "value": .99}]),
                     hive_v3([{"class": "ai_generated", "value": True}]), hive_v3([{"class": "ai_generated", "value": "0.9"}]),
                     hive_v3([{"class": "ai_generated", "value": float("nan")}])):
            self.assertFalse(parse_hive_v3_scores(data)["available"])

    async def test_v3_requires_explicit_billable_media_opt_in(self):
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-only", "HIVE_V3_MEDIA_TYPES": ""}), \
             patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            self.assertFalse((await check_hive_media(valid_png()))["available"])
            post.assert_not_awaited()

    async def test_v3_actual_bytes_bearer_and_combined_single_call(self):
        response = httpx.Response(200, json=hive_v3([{"class": "ai_generated", "value": .98}, {"class": "deepfake", "value": .01}]))
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-only", "HIVE_V3_MEDIA_TYPES": "image"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await image_layers(valid_png(), "image/png", "control.png", auxiliary=False)
        self.assertEqual(post.await_count, 1)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-only")
        self.assertEqual(post.call_args.kwargs["files"]["media"], ("control.png", valid_png(), "image/png"))
        self.assertEqual(result["hive_deepfake"]["shared_request"], "hive")

    async def test_pending_or_errors_do_not_retry(self):
        for status in (202, 401, 402, 429, 500):
            with self.subTest(status=status), patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "test-only", "HIVE_V3_MEDIA_TYPES": "image"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(status))) as post:
                self.assertFalse((await check_hive_media(valid_png()))["available"])
                self.assertEqual(post.await_count, 1)


class TranscriptionAndSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_assembly_upload_pin_model_poll_until_completed(self):
        upload = httpx.Response(200, json={"upload_url": "https://cdn.assemblyai.com/control"})
        job = httpx.Response(200, json={"id": "test-job"})
        responses = [httpx.Response(200, json={"status": "queued"}),
                     httpx.Response(200, json={"status": "completed", "text": "Olá mundo", "words": []})]
        with patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "test-only"}), patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=[upload, job])) as post, \
             patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=responses)) as get, patch("app.services.audio_service.asyncio.sleep", new=AsyncMock()):
            result = await transcribe_with_assemblyai(valid_wav())
        self.assertEqual(result["transcription"], "Olá mundo")
        self.assertEqual(post.call_args.kwargs["json"]["speech_models"], ["universal-2"])
        self.assertEqual(post.call_args_list[0].kwargs["content"], valid_wav())
        self.assertEqual(get.await_count, 2)
        self.assertEqual(result["decision_role"], "transcription_only")

    async def test_assembly_failure_is_unavailable_not_silent_success(self):
        with patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "test-only"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(401, json={"error": "private-secret"}))):
            result = await transcribe_with_assemblyai(valid_wav())
        self.assertFalse(result["available"])
        self.assertNotIn("private-secret", str(result))

    async def test_news_no_result_is_distinct_from_missing_key_and_quota(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": ""}):
            self.assertEqual((await search_news("consulta" )).status, "not_configured")
        with patch.dict(os.environ, {"SERPERAPI_KEY": "test-only"}):
            for status, data, expected in ((200, {"news": []}, "no_results"), (429, {}, "rate_limited"), (200, [], "error")):
                with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(status, json=data))):
                    self.assertEqual((await search_news("consulta")).status, expected)


class GeminiBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_quota_error_is_sanitized_and_not_retried(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_FALLBACK_MODELS": "gemini-2.5-flash"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(429, json={"error": "private-secret"}))) as post:
            with self.assertRaises(GeminiError) as raised:
                await generate_text("Controle")
        self.assertEqual(raised.exception.status, "rate_limited")
        self.assertEqual(raised.exception.http_status, 429)
        self.assertNotIn("private-secret", str(raised.exception))
        self.assertEqual(post.await_count, 1)

    async def test_low_thinking_only_sent_to_gemini_three(self):
        body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"ok":true}'}]}}]}
        for model in ("gemini-3.7-flash", "gemini-2.5-flash"):
            with self.subTest(model=model), patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "GEMINI_MODEL_NAME": model}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=body))) as post:
                value = await generate_text("Controle", max_tokens=64)
                config = post.call_args.kwargs["json"]["generationConfig"]
                self.assertEqual(value.model_name, model)
                self.assertEqual(config["maxOutputTokens"], 64)
                self.assertEqual(config.get("thinkingConfig"), {"thinkingLevel": "LOW"} if model.startswith("gemini-3") else None)

    async def test_invalid_payload_is_typed_failure_without_raw_response(self):
        for body in ([], {"candidates": []}, {"candidates": [None]}, {"candidates": [{"content": {"parts": [{"text": 42}]}}]}):
            with self.subTest(body=body), patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=body))):
                with self.assertRaises(GeminiError) as raised:
                    await generate_text("Controle")
                self.assertEqual(raised.exception.status, "invalid_response")

    def test_auxiliary_media_layers_never_vote_on_authenticity(self):
        result = media_report({"ocr": {"status": "success", "ai_generated_score": 1},
            "audio": {"transcription": "Controle", "transcription_detail": None}}, "audio")
        self.assertEqual(result["analysis_status"], "inconclusive")
        self.assertEqual(result["provider_coverage"]["ocr"]["decision_role"], "ocr_only")
        self.assertIsNone(result["provider_coverage"]["ocr"]["ai_score"])
        self.assertEqual(result["provider_coverage"]["transcription"]["status"], "success")
