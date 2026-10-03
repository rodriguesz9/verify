import json
import os
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from helpers import valid_png
from app.services.hive_service import parse_hive_scores, check_hive_media
from app.core.hive_moderation import _parse_hive_response
from app.core.sightengine_client import check_deepfake
from app.core.huggingface_client import check_ai_image_hf
from app.core.gemini_client import generate_text, GeneratedText
from app.core.gemini_analyzer import extract_text_from_image, analyze_image_with_vision
from app.services.evidence_policy import media_report
from app.services.media_validation import validate_media
from pathlib import Path
from app.api.whatsapp import format_whatsapp_response


def hive_response(classes, code="0", faces=False):
    output = {"bounding_poly": [{"classes": classes}]} if faces else {"classes": classes}
    return {"status": [{"status": {"code": code}, "response": {"output": [output]}}]}


class ProviderParserTests(unittest.TestCase):
    def test_whatsapp_does_not_equate_ai_to_falsehood_or_invent_confidence(self):
        message = format_whatsapp_response({"verdict": "AI_Generated", "score": 20, "analysis_status": "partial"})
        self.assertNotIn("CONTEÚDO FALSO", message)
        self.assertNotIn("%", message)
        self.assertIn("INDÍCIOS", message)

    def test_negative_hive_class_does_not_become_positive(self):
        data = hive_response([{"class": "not_ai_generated", "score": .99}, {"class": "ai_generated", "score": .01}])
        for result in (parse_hive_scores(data), _parse_hive_response(data)):
            self.assertAlmostEqual(result["ai_generated_score"], .01)
            self.assertFalse(result["is_ai_detected"])

    def test_missing_class_and_error_task_are_not_zero_scores(self):
        for data in (hive_response([{"class": "not_ai_generated", "score": .99}]),
                     hive_response([{"class": "ai_generated", "score": .99}], "401"), {}):
            self.assertFalse(parse_hive_scores(data)["available"])
            self.assertIsNone(parse_hive_scores(data).get("ai_generated_score"))

    def test_hive_deepfake_nested_face_classes(self):
        result = parse_hive_scores(hive_response([{"class": "no_deepfake", "score": .01}, {"class": "yes_deepfake", "score": .99}], faces=True))
        self.assertEqual(result["deepfake_score"], .99)

    def test_hive_audio_segments_are_preserved_not_average_truth(self):
        data = {"status": [{"status": {"code": "0"}, "response": {"output": [
            {"time": 0, "end_time": 10, "classes": [{"class": "ai_generated", "score": .98}]},
            {"time": 10, "end_time": 20, "classes": [{"class": "ai_generated", "score": .02}]}]}}]}
        result = parse_hive_scores(data)
        self.assertEqual(result["ai_generated_score"], .98)
        self.assertEqual(len(result["segments"]), 2)
        self.assertEqual(result["segments"][1]["start_seconds"], 10)
        self.assertIn("not_probability_of_whole_file", result["score_aggregation"])

    def test_partial_hive_task_cannot_supply_complete_consensus(self):
        data = hive_response([{"class": "ai_generated", "score": .99}])
        data["status"].append({"status": None})
        result = parse_hive_scores(data)
        self.assertEqual(result["status"], "partial")
        report = media_report({"hive": result, "sightengine": {"available": True, "genai_probability": .99}})
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_invalid_scores_are_rejected(self):
        for value in (True, float("nan"), float("inf"), 2, -1, "0.99"):
            self.assertFalse(parse_hive_scores(hive_response([{"class": "ai_generated", "score": value}]))["available"])

    def test_facial_manipulation_does_not_require_generated_image_class(self):
        result = media_report({"sightengine": {"available": True, "deepfake_probability": .99},
                               "hive": {"available": True, "deepfake_score": .98}})
        self.assertEqual(result["verdict"], "Manipulated")
        self.assertIsNone(result["confidence"])
        self.assertEqual(result["provider_coverage"]["sightengine"]["status"], "success")

    def test_dedicated_hive_facial_model_is_one_provider_not_two_votes(self):
        result = media_report({"hive": {"available": True, "deepfake_score": .99},
                               "hive_deepfake": {"available": True, "deepfake_score": .99}})
        self.assertEqual(result["analysis_status"], "inconclusive")
        result = media_report({"sightengine": {"available": True, "deepfake_probability": .99},
                               "hive_deepfake": {"available": True, "deepfake_score": .99}})
        self.assertEqual(result["verdict"], "Manipulated")
        self.assertEqual(result["provider_coverage"]["hive_deepfake"]["deepfake_score"], .99)


class ProviderTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_hive_deepfake_requires_own_key_not_legacy_fallback(self):
        with patch.dict(os.environ, {"HIVE_API_KEY": "legacy-image-test", "HIVE_DEEPFAKE_API_KEY": ""}), \
             patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
            result = await check_hive_media(valid_png(), "control.png", "deepfake")
        self.assertFalse(result["available"])
        post.assert_not_awaited()
        response = httpx.Response(200, json=hive_response([{"class": "yes_deepfake", "score": .99}], faces=True))
        with patch.dict(os.environ, {"HIVE_API_KEY": "legacy-image-test", "HIVE_DEEPFAKE_API_KEY": "facial-test"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await check_hive_media(valid_png(), "control.png", "deepfake")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "token facial-test")
        self.assertEqual(result["deepfake_score"], .99)

    async def test_hf_missing_or_unsafe_endpoint_never_sends_token(self):
        for endpoint in ("", "http://router.huggingface.co/model", "https://router.huggingface.co.evil.test/model", "https://user:secret@router.huggingface.co/model"):
            with patch("app.core.huggingface_client.HUGGINGFACE_API_TOKEN", "test-only"), \
                 patch("app.core.huggingface_client.API_URL", endpoint), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
                self.assertFalse((await check_ai_image_hf(valid_png()))["available"])
                post.assert_not_awaited()

    async def test_hf_actual_bytes_and_exact_configured_positive_class(self):
        response = httpx.Response(200, json=[{"label": "not_ai_generated", "score": .99}, {"label": "ai_generated", "score": .01}],
                                  request=httpx.Request("POST", "https://router.huggingface.co/control"))
        with patch("app.core.huggingface_client.HUGGINGFACE_API_TOKEN", "test-only"), \
             patch("app.core.huggingface_client.API_URL", "https://router.huggingface.co/control"), \
             patch.dict(os.environ, {"HUGGINGFACE_AI_LABEL": "ai_generated"}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await check_ai_image_hf(valid_png())
        self.assertEqual(result["ai_probability"], .01)
        self.assertEqual(post.call_args.kwargs["content"], valid_png())
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "image/png")

    async def test_hf_invalid_or_missing_positive_class_is_not_zero(self):
        for payload in ({"error": "missing"}, [{"label": "not_ai_generated", "score": .99}], [{"label": "artificial", "score": True}]):
            response = httpx.Response(200, json=payload, request=httpx.Request("POST", "https://router.huggingface.co/control"))
            with patch("app.core.huggingface_client.HUGGINGFACE_API_TOKEN", "test-only"), \
                 patch("app.core.huggingface_client.API_URL", "https://router.huggingface.co/control"), \
                 patch.dict(os.environ, {"HUGGINGFACE_AI_LABEL": "artificial"}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)):
                result = await check_ai_image_hf(valid_png())
            self.assertFalse(result["available"])
            self.assertIsNone(result.get("ai_probability"))

    async def test_sightengine_reads_documented_type_fields(self):
        response = httpx.Response(200, json={"status": "success", "type": {"ai_generated": .97, "deepfake": .02}}, request=httpx.Request("POST", "https://example.test"))
        with patch("app.core.sightengine_client.SIGHTENGINE_API_USER", "test"), patch("app.core.sightengine_client.SIGHTENGINE_API_SECRET", "test"), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await check_deepfake(valid_png())
        self.assertEqual(result["genai_probability"], .97)
        self.assertEqual(result["deepfake_probability"], .02)
        self.assertIn("data", post.call_args.kwargs)
        self.assertNotIn("params", post.call_args.kwargs)

    async def test_hive_audio_uses_its_own_project_key(self):
        response = httpx.Response(200, json=hive_response([{"class": "ai_generated", "score": .03}]))
        with patch.dict(os.environ, {"HIVE_API_KEY": "image-test", "HIVE_AUDIO_API_KEY": "audio-test"}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await check_hive_media(b"fixture", "sample.wav", "audio")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "token audio-test")
        self.assertEqual(result["ai_generated_score"], .03)

    async def test_gemini_honors_model_and_sends_actual_image_bytes(self):
        response = httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"text":"Olá"}'}]}}]})
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "GEMINI_MODEL_NAME": "explicit-model", "GEMINI_FALLBACK_MODELS": ""}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            result = await generate_text([{"inline_data": {"data": b"real-bytes", "mime_type": "image/png"}}])
        self.assertEqual(result.model_name, "explicit-model")
        self.assertIn("/explicit-model:", post.call_args.args[0])
        inline = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["inlineData"]
        import base64
        self.assertEqual(base64.b64decode(inline["data"]), b"real-bytes")

    async def test_gemini_incomplete_output_is_rejected(self):
        response = httpx.Response(200, json={"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "truncated"}]}}]})
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)):
            with self.assertRaises(RuntimeError):
                await generate_text("test")

    async def test_ocr_and_vision_work_with_a_configured_key(self):
        ocr = GeneratedText(json.dumps({"text": "R$ 10"})); ocr.model_name = "test-model"
        vision = GeneratedText(json.dumps({"visual_forensics_verdict": "Suspicious", "visual_score": 50})); vision.model_name = "test-model"
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), patch("app.core.gemini_analyzer.generate_text", new=AsyncMock(side_effect=[ocr, vision])):
            self.assertEqual((await extract_text_from_image(valid_png(), "image/png"))["status"], "success")
            self.assertEqual((await analyze_image_with_vision(valid_png(), "image/png", {}))["status"], "success")

    async def test_recorded_webm_without_duration_is_decoded(self):
        data = (Path(__file__).parent / "fixtures/recorder-no-duration.webm").read_bytes()
        result = await validate_media(data, "recorded.webm", "audio/webm")
        self.assertEqual(result.kind, "audio")
        self.assertGreater(result.details["duration_seconds"], .9)
        self.assertLess(result.details["duration_seconds"], 1.2)
