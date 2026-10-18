"""Narrow PT/EN descriptor aliases, not translations of arbitrary entities."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
from app.core.openrouter_service import GeneratedText
from app.services.source_corroboration import _passage_guard, _same_event, corroborate_sources


STAMP = "2026-10-17T12:00:00+00:00"


class InstrumentNameAliasTests(unittest.IsolatedAsyncioTestCase):
    claim = "O Telescópio Espacial James Webb foi lançado em 25 de dezembro de 2021."
    quote = "The James Webb Space Telescope was launched on December 25, 2021."

    def guard(self, quote, claim=None, relation="supports"):
        return _passage_guard(claim or self.claim, {"quote": quote, "context": quote}, relation, STAMP)

    def test_descriptors_match_but_named_instrument_is_not_replaced(self):
        self.assertTrue(_same_event(self.claim, self.quote))
        self.assertIsNone(self.guard(self.quote))
        for changed in (self.quote.replace("James Webb", "Hubble"),
                        self.quote.replace("Telescope", "Station"),
                        self.quote.replace("December 25", "December 26"),
                        self.quote.replace("2021", "2022"),
                        self.quote.replace("was launched", "will be launched"),
                        "A mission announced on December 25, 2021 discussed the James Webb Space Telescope launch."):
            with self.subTest(quote=changed):
                self.assertIsNotNone(self.guard(changed))

    def test_generic_descriptor_translation_works_for_other_identified_instrument(self):
        claim = "O Telescópio Espacial Aurora foi lançado em 17 de julho de 2011."
        quote = "The Aurora Space Telescope was launched on July 17, 2011."
        self.assertIsNone(self.guard(quote, claim))
        self.assertIsNotNone(self.guard(quote.replace("Aurora", "Atlas"), claim))

    async def test_two_literal_independent_bodies_can_be_compared_without_rewriting(self):
        docs = [{"url": url, "title": "Instrument record", "sentences": [quote],
                 "sentence_roles": ["body"], "retrieved_at": STAMP, "truncated": False}
                for url, quote in (("https://www.nasa.gov/mission/instrument-record", self.quote),
                                   ("https://agenciabrasil.ebc.com.br/controle-instrumento", self.claim))]
        async def answer(prompt, **_kwargs):
            request = json.loads(prompt)
            return GeneratedText(json.dumps({"claims": [{"claim_id": "c1", "evidence": [
                {"source_id": source["source_id"], "excerpt_id": source["passages"][0]["excerpt_id"],
                 "relation": "supports"} for source in request["sources"]]}]}))
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=answer)) as model:
            result = await corroborate_sources(self.claim, docs)
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual({item["excerpt"] for item in result["claims"][0]["evidence"]}, {self.claim, self.quote})
        model.assert_awaited_once()
