"""Closed active launch BODY controls, invented missions/dates and no APIs."""
import unittest

from app.services.launch_body_dates import (
    launch_body_temporal_anchor, launch_body_dated_reading, launch_date_claim_matches_body,
)
from app.services.launch_relations import launch_date_relation


DAY = "2002-03-10"  # Sunday, synthetic calendar control.
QUOTE = "A Agência Delta lançou na madrugada deste domingo (10/3) a missão Aurora 4."
CLAIM = "A missão Aurora IV foi lançada em 10 de março de 2001."
TAIL = (", primeiro voo do foguete Zeta (Sistema Espacial Delta) com a cápsula Omega, "
        "destinada a levar humanos de volta à Lua.")


class ActiveLaunchBodyDateTests(unittest.TestCase):
    def test_completed_agency_action_dates_its_explicit_numbered_mission_object(self):
        anchor = launch_body_temporal_anchor(QUOTE, DAY)
        self.assertEqual(anchor, {"kind": "explicit_active_mission_launch_body_date",
            "expression": "na madrugada deste domingo (10/3)", "publication_date": DAY,
            "mission_identity": {"program": "aurora", "number": 4}})
        reading = launch_body_dated_reading(QUOTE, anchor)
        self.assertEqual(reading, "A missão Aurora 4 foi lançada em 2002-03-10.")
        self.assertTrue(launch_date_claim_matches_body(CLAIM, QUOTE))
        self.assertEqual(launch_date_relation(CLAIM, reading), "refutes")
        self.assertEqual(launch_date_relation(CLAIM.replace("2001", "2002"), reading), "supports")

    def test_numeric_roman_identity_and_names_are_generic(self):
        for name, equivalent in (("Aurora 4", "Aurora IV"), ("Beta Delta IX", "Beta Delta 9"),
                                 ("Zeta I", "Zeta 1")):
            with self.subTest(name=name):
                quote = QUOTE.replace("Aurora 4", name)
                claim = CLAIM.replace("Aurora IV", equivalent)
                self.assertTrue(launch_date_claim_matches_body(claim, quote))
                anchor = launch_body_temporal_anchor(quote, DAY)
                self.assertEqual(launch_date_relation(claim, launch_body_dated_reading(quote, anchor)), "refutes")
        self.assertIsNone(launch_body_temporal_anchor(QUOTE.replace("Aurora 4", "Aurora IIII"), DAY))

    def test_whole_closed_nominal_complement_preserves_original_body(self):
        for destination in ("à Lua", "ao Planeta Zeta", "à Terra", "ao Marte"):
            quote = QUOTE[:-1] + TAIL.replace("à Lua", destination)
            with self.subTest(destination=destination):
                anchor = launch_body_temporal_anchor(quote, DAY)
                self.assertIsNotNone(anchor)
                self.assertEqual(launch_body_dated_reading(quote, anchor), "A missão Aurora 4 foi lançada em 2002-03-10.")
                self.assertTrue(launch_date_claim_matches_body(CLAIM, quote))
                self.assertIn("primeiro voo do foguete Zeta", quote)
                self.assertEqual(quote, QUOTE[:-1] + TAIL.replace("à Lua", destination))
        no_expansion = QUOTE[:-1] + TAIL.replace(" (Sistema Espacial Delta)", "")
        self.assertIsNotNone(launch_body_temporal_anchor(no_expansion, DAY))

    def test_weekday_day_month_and_explicit_publication_metadata_must_agree(self):
        for quote in (QUOTE.replace("domingo", "segunda-feira"), QUOTE.replace("(10/3)", "(11/3)"),
                      QUOTE.replace("(10/3)", "(10/4)"), QUOTE.replace(" (10/3)", ""),
                      QUOTE.replace("na madrugada deste domingo (10/3)", "em março")):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_body_temporal_anchor(quote, DAY))
        for metadata in (None, "", "2002-03-11", "2002-04-10", "2001-03-10", "2002-02-30",
                         "https://example.test/2002/03/10", "Título: 2002-03-10", DAY + "T12:00:00Z"):
            self.assertIsNone(launch_body_temporal_anchor(QUOTE, metadata))

    def test_date_only_claim_cannot_lose_owner_instrument_or_other_qualifiers(self):
        for claim in (CLAIM.replace("Aurora IV", "Aurora V"), CLAIM.replace("Aurora", "Beta"),
                      CLAIM.replace("A missão", "A nave"), CLAIM.replace("A missão", "O foguete"),
                      CLAIM.replace("Aurora IV", "Aurora IV da Agência Delta"),
                      CLAIM.replace("foi lançada", "foi lançada com sucesso"),
                      CLAIM.replace("A missão", "A missão tripulada"),
                      CLAIM[:-1] + " da Base Zeta.", CLAIM[:-1] + " às 04:00 UTC.",
                      CLAIM[:-1] + " e retornou à Terra.", CLAIM + " Levou humanos à Lua."):
            with self.subTest(claim=claim):
                self.assertFalse(launch_date_claim_matches_body(claim, QUOTE))

    def test_plans_negation_reporting_quotes_conditions_and_other_actions_abstain(self):
        for quote in (QUOTE.replace("lançou", "não lançou"), QUOTE.replace("lançou", "lançará"),
                      QUOTE.replace("lançou", "planeja lançar"), QUOTE.replace("lançou", "pode ter lançado"),
                      "Segundo um jornalista, " + QUOTE, "A agência anunciou que " + QUOTE,
                      "Se " + QUOTE[2:], "Caso " + QUOTE[2:], "Relato " + QUOTE[2:],
                      "Sem " + QUOTE[2:], "Em Sonho " + QUOTE[2:],
                      QUOTE.replace("Agência Delta", "Agência Suposta Delta"),
                      QUOTE.replace("Agência Delta", "Agência Fictícia Delta"),
                      "Publicado " + QUOTE[2:], '"' + QUOTE + '"', "‘" + QUOTE + "’",
                      QUOTE[:-1] + "?", QUOTE + " Depois retornou à Terra.",
                      QUOTE.replace("Agência Delta", "Agência Delta, que retornou ontem,"),
                      QUOTE.replace("lançou", "pousou e lançou"),
                      QUOTE.replace("Aurora 4", "Aurora 4 e a missão Zeta 2"),
                      QUOTE.replace("a missão Aurora 4", "o foguete Aurora 4")):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_body_temporal_anchor(quote, DAY))

    def test_unknown_tail_other_dates_or_subordinate_predicates_cannot_be_dropped(self):
        for tail in (", com destino à Lua.", ", primeiro voo.", ", missão prevista.",
                     ", em 9 de março de 2002.", " em outro domingo (17/3).",
                     ", que retornou à Terra.", ", conforme relatou Zeta.",
                     TAIL.replace("destinada a levar humanos", "que levou humanos"),
                     TAIL.replace("primeiro voo", "segundo voo"),
                     TAIL.replace("Lua", "Lua e Marte"), TAIL[:-1] + " e retornou."):
            quote = QUOTE[:-1] + tail
            with self.subTest(tail=tail):
                self.assertIsNone(launch_body_temporal_anchor(quote, DAY))

    def test_anchor_revalidation_rejects_changed_quote_or_proof_fields(self):
        anchor = launch_body_temporal_anchor(QUOTE, DAY)
        for changed in ({**anchor, "publication_date": "2002-03-11"},
                        {**anchor, "mission_identity": {"program": "beta", "number": 4}},
                        {**anchor, "expression": "neste domingo (10/3)"},
                        {**anchor, "extra": True}, None, {}):
            self.assertIsNone(launch_body_dated_reading(QUOTE, changed))
        self.assertIsNone(launch_body_dated_reading(QUOTE.replace("Aurora 4", "Aurora 5"), anchor))
        self.assertIsNone(launch_body_dated_reading(QUOTE + " Outra missão pousou.", anchor))

    def test_passive_reading_contract_remains_literal(self):
        quote = "O telescópio espacial Zeta Omega foi lançado neste domingo (10/3)."
        anchor = launch_body_temporal_anchor(quote, DAY)
        self.assertEqual(anchor["kind"], "explicit_launch_body_date")
        self.assertEqual(launch_body_dated_reading(quote, anchor),
                         "O telescópio espacial Zeta Omega foi lançado em 2002-03-10.")


if __name__ == "__main__":
    unittest.main()
