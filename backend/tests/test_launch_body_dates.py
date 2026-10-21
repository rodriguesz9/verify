"""Pure passive-body date binding; no APIs, known mission dates or verdicts."""
import unittest

from app.services.launch_body_dates import launch_body_temporal_anchor


DAY = "2002-03-10"  # Sunday, synthetic control date, not a known launch lookup.
SIMPLE = "O telescópio espacial Zeta Omega foi lançado neste domingo (10/3)."
INTRO = ("Nasa lança com sucesso telescópio Zeta Omega Em uma missão histórica, "
         "o telescópio espacial Zeta Omega foi lançado pela Nasa na manhã deste domingo (10) "
         "a partir de uma base da Agência Espacial Delta (AED) na Guiana Leste.")


class LaunchBodyDateTests(unittest.TestCase):
    def test_simple_completed_passive_requires_explicit_relative_date(self):
        self.assertEqual(launch_body_temporal_anchor(SIMPLE, DAY), {
            "kind": "explicit_launch_body_date", "expression": "neste domingo (10/3)", "publication_date": DAY})

    def test_intro_repeats_same_instrument_and_preserves_agency_location_and_period_of_day(self):
        quote = INTRO
        result = launch_body_temporal_anchor(quote, DAY)
        self.assertEqual(result, {"kind": "explicit_launch_body_date",
            "expression": "na manhã deste domingo (10)", "publication_date": DAY})
        self.assertEqual(quote, INTRO)
        self.assertIn("pela Nasa", quote)
        self.assertIn("Guiana Leste", quote)
        self.assertNotIn("2002-03-10", quote)

    def test_closed_mission_and_agency_forms(self):
        for quote in (
            "A missão Aurora IX foi lançada nesta domingo (10/3).",
            "O satélite Aurora 9 foi lançado pela NASA na tarde deste domingo (10/3) na Base Alfa.",
            "A nave Aurora IX foi lançada pela Agência Espacial Delta (AED) na noite deste domingo (10).",
        ):
            with self.subTest(quote=quote):
                self.assertIsNotNone(launch_body_temporal_anchor(quote, DAY))

    def test_missing_invalid_mismatched_or_non_metadata_date_abstains(self):
        for publication in (None, "", "2002-03-11", "2002-04-10", "2001-03-10", "2002-02-30",
                            "https://example.test/2002/03/10", "10/03/2002", DAY + "T12:00:00Z"):
            with self.subTest(publication=publication):
                self.assertIsNone(launch_body_temporal_anchor(SIMPLE, publication))

    def test_weekday_day_and_optional_month_all_must_agree(self):
        for quote in (SIMPLE.replace("domingo", "sábado"), SIMPLE.replace("(10/3)", "(11/3)"),
                      SIMPLE.replace("(10/3)", "(10/4)"), SIMPLE.replace("(10/3)", "(32/3)"),
                      SIMPLE.replace(" (10/3)", ""), SIMPLE.replace("neste domingo ", "")):
            self.assertIsNone(launch_body_temporal_anchor(quote, DAY))

    def test_planning_negation_reported_claim_and_second_action_are_not_dropped(self):
        for quote in (
            SIMPLE.replace("foi lançado", "será lançado"),
            SIMPLE.replace("foi lançado", "não foi lançado"),
            SIMPLE.replace("foi lançado", "Não foi lançado"),
            "Segundo Carlos, " + SIMPLE,
            "A agência anunciou que " + SIMPLE,
            "É falso que " + SIMPLE,
            SIMPLE + " Outra missão pousou no dia seguinte.",
            SIMPLE.replace("foi lançado", "foi construído e foi lançado"),
            SIMPLE.replace(" neste", " depois de pousar neste"),
            SIMPLE.replace(" neste", " após anunciar nesta"),
            SIMPLE.replace("foi lançado", "pode ter sido lançado"),
            SIMPLE.replace("Zeta Omega", "Zeta Pousou"),
        ):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_body_temporal_anchor(quote, DAY))

    def test_intro_other_object_cannot_lend_its_launch_or_date_to_body(self):
        self.assertIsNone(launch_body_temporal_anchor(INTRO.replace("telescópio Zeta Omega Em", "telescópio Beta Delta Em"), DAY))
        self.assertIsNone(launch_body_temporal_anchor(INTRO.replace("Em uma missão histórica,", "Em uma missão prevista,"), DAY))

    def test_unknown_bridge_cannot_hide_extra_action_or_borrow_another_date(self):
        for bridge in ("pela Nasa, que anunciou outro evento,", "pela Nasa após sua construção",
                       "pela Nasa em 9 de março de 2002", "pela agência não identificada"):
            self.assertIsNone(launch_body_temporal_anchor(SIMPLE.replace("foi lançado", "foi lançado " + bridge), DAY))

    def test_helper_does_not_decide_identity_or_verdict(self):
        original = launch_body_temporal_anchor(SIMPLE, DAY)
        other = launch_body_temporal_anchor(SIMPLE.replace("Zeta Omega", "Beta Delta"), DAY)
        self.assertEqual(original, other)
        self.assertEqual(set(original), {"kind", "expression", "publication_date"})


if __name__ == "__main__":
    unittest.main()
