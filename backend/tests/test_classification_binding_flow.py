"""Classification grammar still needs independent bodies and full model review."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_corroboration as sources
import test_classification_body_dates as controls

CLAIM = controls.ClassificationBodyDatesTests.claim
DEFINITION = controls.ClassificationBodyDatesTests.definition
BRIDGE = controls.ClassificationBodyDatesTests.bridge
COORDINATED = controls.ClassificationBodyDatesTests.coordinated
FIRST = " ".join((DEFINITION, BRIDGE, COORDINATED))
SECOND = "Conselho Aurora declarou uma emergência regional em 7 de março de 2014 e caracterizou FA-7 como uma pandemia em 18 de abril de 2014."
STAMP = "2026-10-23T12:00:00+00:00"


def documents():
    return [{"url": url, "title": "Registro público", "sentences": body,
             "sentence_roles": ["body"] * len(body), "retrieved_at": STAMP, "truncated": False}
            for url, body in (("https://www.bbc.com/example", [DEFINITION, BRIDGE, COORDINATED]),
                              ("https://www.cnn.com/example", [SECOND]))]


class ClassificationBindingFlowTests(unittest.IsolatedAsyncioTestCase):
    async def compare(self, docs, *, insufficient=False, incomplete=False):
        def answer(prompt, **_kwargs):
            request = json.loads(prompt)
            rows = [{"source_id": src["source_id"], "assessment": "insufficient" if insufficient else "evidence",
                     "evidence": [] if insufficient else [{"excerpt_id": src["passages"][0]["excerpt_id"], "relation": "supports"}]}
                    for src in request["sources"]]
            return json.dumps({"claims": [{"claim_id": "c1", "source_reviews": rows[:1] if incomplete else rows}]})
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini"}), \
             patch.object(sources.gemini_client, "generate_text", new=AsyncMock(side_effect=answer)) as model, \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock()) as alternate:
            result = await sources.corroborate_sources(CLAIM, docs)
        alternate.assert_not_awaited()
        return result, model

    async def test_two_independent_complete_bodies_are_reviewed_and_quotes_stay_literal(self):
        result, model = await self.compare(documents())
        model.assert_awaited_once()
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["coverage"]["eligible_family_count"], 2)
        evidence = result["claims"][0]["evidence"]
        self.assertEqual({item["excerpt"] for item in evidence}, {FIRST, SECOND})
        proof = next(item["classification_body_binding"] for item in evidence if item["excerpt"] == FIRST)
        self.assertEqual(proof["quote"], FIRST)
        self.assertEqual([c["date"] for c in proof["clauses"]], ["2014-03-07", "2014-04-18"])

    async def test_one_editorial_family_still_cannot_decide_or_trigger_model(self):
        result, model = await self.compare(documents()[:1])
        model.assert_not_awaited()
        self.assertEqual(result["state"], "insufficient")

    async def test_model_insufficiency_and_incomplete_review_are_not_repaired_into_agreement(self):
        for options in ({"insufficient": True}, {"incomplete": True}):
            with self.subTest(options=options):
                result, model = await self.compare(documents(), **options)
                model.assert_awaited_once()
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["claims"][0]["evidence"], [])

    def test_wrong_date_denial_fiction_future_and_wrong_subject_do_not_gain_a_bypass(self):
        for claim, quote, context, stamp, relation in (
            (CLAIM.replace("18 de abril", "7 de março"), FIRST, FIRST, STAMP, "supports"),
            (CLAIM, FIRST, "Texto fictício. " + FIRST, STAMP, "supports"),
            (CLAIM, FIRST, FIRST + " O órgão não fez essa caracterização.", STAMP, "supports"),
            (CLAIM, FIRST, FIRST, "2014-04-17T12:00:00+00:00", "supports"),
            (CLAIM, FIRST, FIRST, STAMP, "refutes"),
            (CLAIM.replace("FA-7", "FA-8"), FIRST, FIRST, STAMP, "supports"),
        ):
            with self.subTest(claim=claim, relation=relation, stamp=stamp):
                self.assertIsNotNone(sources._passage_guard(claim, {"quote": quote, "context": context}, relation, stamp))


if __name__ == "__main__":
    unittest.main()
