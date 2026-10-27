"""Complete JSON formatting must not rewrite literal OCR or accept hidden prose."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core.gemini_analyzer import _extract_json_text, _extract_image_text_remote
from app.core.gemini_client import GeneratedText
from helpers import valid_png


class AuxiliaryEnvelopeTests(unittest.TestCase):
    def test_backticks_inside_json_string_are_preserved_literally(self):
        text = 'Não pague R$ 123,45. Data 03/10/2026. Exemplo: ```json {"pagar": false} ```'
        raw = json.dumps({"text": text}, ensure_ascii=False)
        self.assertEqual(json.loads(_extract_json_text(raw)), {"text": text})

    def test_whole_envelope_supports_plain_json_and_one_complete_json_fence(self):
        raw = json.dumps({"text": "Não pague R$ 123,45 em 03/10/2026."}, ensure_ascii=False)
        for value in (raw, "  " + raw + "\n", "```json\n" + raw + "\n```", "```JSON\r\n" + raw + "\r\n```", "```\n" + raw + "\n```"):
            with self.subTest(value=value):
                self.assertEqual(json.loads(_extract_json_text(value)), json.loads(raw))

    def test_prose_partial_or_multiple_blocks_are_not_scanned_for_a_valid_fragment(self):
        raw = '{"text":"Não pague."}'
        for value in ('Explicação\n```json\n' + raw + '\n```', '```json\n' + raw + '\n```\nExplicação',
                      '```python\n' + raw + '\n```', '```json\n' + raw, raw + raw,
                      '```json\n' + raw + '\n```\n```json\n' + raw + '\n```'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                json.loads(_extract_json_text(value))

    def test_original_length_limit_is_checked_before_stripping(self):
        with self.assertRaises(ValueError):
            _extract_json_text(' ' * 30000 + '{}')
        for value in (None, {}, 3):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _extract_json_text(value)


class RemoteOCRFieldsTests(unittest.IsolatedAsyncioTestCase):
    async def test_ocr_keeps_only_literal_text_and_server_owned_metadata(self):
        text = 'Não pague. Valor: R$ 123,45. Data: 03/10/2026. ```json {"pagar": false} ```'
        raw = GeneratedText(json.dumps({"text": text, "verdict": "Authentic", "confidence": 100,
            "limitations": [], "fallback_status": "success", "http_status": 200}, ensure_ascii=False))
        raw.model_name = 'offline-control'
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
                patch('app.core.gemini_analyzer.generate_text', new=AsyncMock(return_value=raw)), \
                patch('app.core.openrouter_service.extract_image_text', new=AsyncMock()) as fallback:
            result = await _extract_image_text_remote(valid_png(), 'image/png')
        fallback.assert_not_awaited()
        self.assertEqual(result, {"text": text, "available": True, "status": "success",
            "model_used": "offline-control", "provider": "gemini", "decision_role": "ocr_only"})

    async def test_explanatory_prose_with_embedded_valid_block_is_technical_failure(self):
        raw = GeneratedText('Explicação não solicitada\n```json\n{"text":"Não pague."}\n```')
        raw.model_name = 'offline-control'
        alternate = {"available": False, "status": "not_configured", "text": ""}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "offline-control"}), \
                patch('app.core.gemini_analyzer.generate_text', new=AsyncMock(return_value=raw)), \
                patch('app.core.openrouter_service.extract_image_text', new=AsyncMock(return_value=alternate)) as fallback:
            result = await _extract_image_text_remote(valid_png(), 'image/png')
        fallback.assert_awaited_once()
        self.assertFalse(result['available'])
        self.assertEqual(result['text'], '')
