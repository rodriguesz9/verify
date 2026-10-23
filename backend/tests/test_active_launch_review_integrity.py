"""Completed BODY launch proof through policy; never synthetic truth labels."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_corroboration import corroborate_sources, _candidate_passage, _passage_guard


CLAIM = "A missão Aurora IV foi lançada em 10 de março de 2001."
QUOTE = "A Agência Delta lançou na madrugada deste domingo (10/3) a missão Aurora 4."
STAMP = "2026-10-22T12:00:00+00:00"


def documents(prefix=None, suffix=None, role="body", publication="2002-03-10"):
    result = []
    for url, agency in (("https://www.bbc.com/control", "Delta"), ("https://www.cnn.com/control", "Beta")):
        sentences = ([prefix] if prefix else []) + [QUOTE.replace("Delta", agency)] + ([suffix] if suffix else [])
        roles = (["context"] if prefix else []) + [role] + (["body"] if suffix else [])
        result.append({"url": url, "sentences": sentences, "sentence_roles": roles,
                       "publication_date": publication, "retrieved_at": STAMP, "truncated": False})
    return result


class ActiveLaunchReviewIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, claim=CLAIM, docs=None):
        with patch("app.services.source_corroboration.gemini_client.generate_text", new=AsyncMock()) as gemini, \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock()) as router:
            result = await corroborate_sources(claim, documents() if docs is None else docs)
        gemini.assert_not_awaited()
        router.assert_not_awaited()
        return result

    async def test_literal_quote_original_identity_and_date_proof_survive_internal_reading(self):
        result = await self.check()
        self.assertEqual(result["state"], "refuted")
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")
        self.assertEqual({entry["excerpt"] for entry in result["claims"][0]["evidence"]},
                         {QUOTE, QUOTE.replace("Delta", "Beta")})
        self.assertTrue(all(entry["launch_anchor"]["publication_date"] == "2002-03-10"
                            for entry in result["claims"][0]["evidence"]))
        supported = await self.check(CLAIM.replace("2001", "2002"))
        self.assertEqual(supported["state"], "corroborated")
        uncrewed = await self.check(docs=documents(suffix="Essa missão não tripulada transportou instrumentos."))
        self.assertEqual(uncrewed["state"], "refuted")

    async def test_actual_context_fiction_conditions_and_adjacent_denial_are_not_erased(self):
        for prefix in ("Relato fictício.", "Uma simulação.", "Uma hipótese.", "Se isso ocorreu.", "Talvez tenha ocorrido."):
            with self.subTest(prefix=prefix):
                self.assertEqual((await self.check(docs=documents(prefix=prefix)))["state"], "insufficient")
        for suffix in ("Essa missão não foi lançada.", "O lançamento é fictício.", "Isso é uma simulação."):
            with self.subTest(suffix=suffix):
                self.assertEqual((await self.check(docs=documents(suffix=suffix)))["state"], "insufficient")

    async def test_heading_date_alone_wrong_metadata_and_extra_claimed_qualifiers_cannot_vote(self):
        for docs in (documents(role="context"), documents(publication=None), documents(publication="2002-03-11")):
            self.assertEqual((await self.check(docs=docs))["state"], "insufficient")
        for claim in (CLAIM[:-1] + " da Base Zeta.", CLAIM.replace("foi lançada", "foi lançada com sucesso"),
                      CLAIM.replace("Aurora IV", "Aurora IV da Agência Delta")):
            self.assertEqual((await self.check(claim))["state"], "insufficient")

    def test_future_publication_and_tampered_identity_are_vetoed(self):
        raw = documents()[0]
        passage = _candidate_passage(QUOTE, QUOTE, raw)
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", "2001-03-10T12:00:00+00:00"))
        passage["launch_anchor"]["mission_identity"]["number"] = 5
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", STAMP))
