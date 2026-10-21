"""Relative launch date integration; no network or measured precision."""
import unittest

from app.services.source_corroboration import _candidate_passage, _passage_guard, _prepare_sources
from app.services.launch_body_dates import launch_date_claim_matches_body


CLAIM = "O Telescópio Espacial Zeta Omega foi lançado em 10 de março de 2002."
QUOTE = ("Nasa lança com sucesso telescópio Zeta Omega Em uma missão histórica, "
         "o telescópio espacial Zeta Omega foi lançado pela Nasa na manhã deste domingo (10) "
         "a partir de uma base da Agência Espacial Delta (AED) na Guiana Leste.")
STAMP = "2026-10-20T12:00:00+00:00"


class LaunchBodyDateFlowTests(unittest.TestCase):
    def raw(self, **changes):
        return {"url": "https://g1.globo.com/control", "title": "Controle",
            "sentences": [QUOTE], "sentence_roles": ["body"], "publication_date": "2002-03-10",
            "retrieved_at": STAMP, "truncated": False, **changes}

    def test_publication_and_literal_weekday_day_bind_same_named_date_only_claim(self):
        raw = self.raw()
        passage = _candidate_passage(QUOTE, QUOTE, raw)
        self.assertTrue(launch_date_claim_matches_body(CLAIM, QUOTE))
        self.assertIsNone(_passage_guard(CLAIM, passage, "supports", STAMP))
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "refutes", STAMP))
        self.assertEqual(passage["quote"], QUOTE)
        sources, _, _, _ = _prepare_sources([raw], [CLAIM], None)
        self.assertEqual(len(sources), 1)

    def test_date_link_never_supplies_claimed_agency_location_time_or_success(self):
        for claim in (CLAIM.replace("foi lançado", "da Nasa foi lançado"),
                      CLAIM.replace("lançado em", "lançado com sucesso em"),
                      CLAIM[:-1] + " pela Nasa.", CLAIM[:-1] + " na Guiana Leste.",
                      CLAIM[:-1] + " às 08:00.", CLAIM.replace("foi lançado", "foi lançado pela ESA")):
            self.assertFalse(launch_date_claim_matches_body(claim, QUOTE), claim)
            passage = _candidate_passage(QUOTE, QUOTE, self.raw())
            self.assertIsNotNone(_passage_guard(claim, passage, "supports", STAMP))

    def test_object_name_word_order_and_instrument_descriptor_cannot_switch(self):
        for claim in (CLAIM.replace("Zeta Omega", "Omega Zeta"), CLAIM.replace("Zeta Omega", "Zeta Alfa"),
                      CLAIM.replace("Telescópio Espacial", "Satélite")):
            self.assertFalse(launch_date_claim_matches_body(claim, QUOTE))
        self.assertFalse(launch_date_claim_matches_body(CLAIM, QUOTE.replace("telescópio espacial", "telescópio")))

    def test_missing_metadata_day_mismatch_heading_or_date_tampering_is_not_evidence(self):
        for raw in (self.raw(publication_date=None), self.raw(publication_date="2002-03-11"),
                    self.raw(sentence_roles=["context"])):
            self.assertEqual(_prepare_sources([raw], [CLAIM], None)[0], [])
        passage = _candidate_passage(QUOTE, QUOTE, self.raw())
        passage["launch_anchor"]["publication_date"] = "2002-03-11"
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "supports", STAMP))

    def test_relative_link_is_not_support_for_other_day_or_future_publication(self):
        passage = _candidate_passage(QUOTE, QUOTE, self.raw())
        self.assertIsNotNone(_passage_guard(CLAIM.replace("10 de março", "11 de março"), passage, "supports", STAMP))
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "supports", "2001-01-01T00:00:00+00:00"))

    def test_context_denial_and_unknown_condition_remain_blocked(self):
        passage = _candidate_passage(QUOTE, "É falso que " + QUOTE, self.raw())
        self.assertIsNotNone(_passage_guard(CLAIM, passage, "supports", STAMP))
        changed = QUOTE.replace("foi lançado", "seria lançado")
        self.assertNotIn("launch_anchor", _candidate_passage(changed, changed, self.raw(sentences=[changed])))


if __name__ == "__main__":
    unittest.main()
