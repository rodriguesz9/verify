"""Unknown grammar remains model-readable; ambiguity never becomes a vote."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_corroboration import corroborate_sources


REFERENCE = "Lei nº 8.541, de 15 de abril de 2010"
CLAIM = f"O artigo 7º da {REFERENCE}, declarou legalmente extinta a taxa no Município Zeta."
QUOTE = "Art. 7º É pelo presente artigo declarada extinta a taxa no Município Zeta."


def documents(quote):
    return [{"url": url, "sentences": [REFERENCE, quote.replace("Art. 7º", label)], "sentence_roles": ["context", "body"],
             "retrieved_at": "2026-10-22T12:00:00+00:00", "truncated": False}
            for url, label in (("https://www.bbc.com/control", "Art. 7º"), ("https://www.cnn.com/control", "Artigo 7º"))]


async def answer(prompt, **kwargs):
    request = json.loads(prompt)
    return json.dumps({"claims": [{"claim_id": "c1", "source_reviews": [
        {"source_id": source["source_id"], "assessment": "evidence", "evidence": [
            {"excerpt_id": source["passages"][0]["excerpt_id"], "relation": "supports"}]}
        for source in request["sources"]]}]})


class LegalFallbackIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_complete_unconditional_style_reaches_guarded_model_review(self):
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=answer)) as model:
            result = await corroborate_sources(CLAIM, documents(QUOTE))
        model.assert_awaited_once()
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["coverage"]["comparison_method"], "model_source_review_v2")

    async def test_closed_reflexive_equivalent_uses_literal_review_without_a_model(self):
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock()) as router, \
             patch("app.services.source_corroboration.gemini_client.generate_text", new=AsyncMock()) as gemini:
            result = await corroborate_sources(CLAIM, documents(QUOTE.replace("É pelo presente artigo declarada", "Declara-se")))
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")
        router.assert_not_awaited()
        gemini.assert_not_awaited()

    async def test_unknown_style_with_omitted_condition_or_exception_stays_insufficient(self):
        for suffix in (" caso haja autorização", " apenas para moradores isentos", ", salvo decisão contrária"):
            with self.subTest(suffix=suffix), patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true"}), \
                 patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock()) as router, \
                 patch("app.services.source_corroboration.gemini_client.generate_text", new=AsyncMock()) as gemini:
                result = await corroborate_sources(CLAIM, documents(QUOTE[:-1] + suffix + "."))
            self.assertEqual(result["state"], "insufficient")
            router.assert_not_awaited()
            gemini.assert_not_awaited()
