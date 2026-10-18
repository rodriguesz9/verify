"""Strict launch abstention cannot escape through generic source guards."""
import unittest

import helpers
from app.services.launch_relations import is_launch_date_claim, launch_date_relation
from app.services.source_corroboration import _passage_guard


STAMP = "2026-10-18T12:00:00+00:00"
QUOTE = "A missão Aurora IV foi lançada em 16 de novembro de 2021."


class LaunchScopeIntegrationTests(unittest.TestCase):
    def assert_launch_scope_rejects(self, claim):
        self.assertTrue(is_launch_date_claim(claim))
        self.assertIsNone(launch_date_relation(claim, QUOTE))
        passage = {"quote": QUOTE, "context": QUOTE}
        self.assertIsNotNone(_passage_guard(claim, passage, "supports", STAMP))
        self.assertIsNotNone(_passage_guard(claim, passage, "refutes", STAMP))

    def test_claimed_crew_quantity_cannot_disappear(self):
        self.assert_launch_scope_rejects(QUOTE[:-1] + " com quatro astronautas.")

    def test_claimed_failed_attempt_qualifier_cannot_disappear(self):
        self.assert_launch_scope_rejects(QUOTE[:-1] + " após uma tentativa fracassada.")

    def test_claimed_first_launch_qualifier_cannot_disappear(self):
        self.assert_launch_scope_rejects(QUOTE[:-1] + " pela primeira vez.")

    def test_year_only_and_planned_mission_launches_cannot_use_generic_fallback(self):
        for claim in ("A missão Aurora IV foi lançada em 2021.",
                      "A missão Aurora IV será lançada em 16 de novembro de 2021."):
            with self.subTest(claim=claim):
                self.assert_launch_scope_rejects(claim)

    def test_repeated_vehicle_frames_cannot_refute_a_different_date(self):
        for quote in (
            "On November 16, 2022, the Saturn V rocket launches on the Aurora IV mission.",
            "Em 16 de novembro de 2022, o foguete Saturn V lançou a espaçonave Aurora IV.",
        ):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_date_relation(QUOTE, quote))
                self.assertIsNotNone(_passage_guard(QUOTE, {"quote": quote, "context": quote}, "refutes", STAMP))

    def test_nominal_and_vehicle_support_still_require_past_dates(self):
        future = QUOTE.replace("2021", "2030")
        for quote in (
            "O lançamento da missão Aurora IV ocorreu em 16 de novembro de 2030.",
            "On November 16, 2030, the Saturn V rocket launches on the Aurora IV mission.",
            "Em 16 de novembro de 2030, o foguete Saturn V lançou a espaçonave Aurora IV.",
        ):
            with self.subTest(quote=quote):
                self.assertEqual(launch_date_relation(future, quote), "supports")
                self.assertIsNotNone(_passage_guard(future, {"quote": quote, "context": quote}, "supports", STAMP))

    def test_vehicle_payload_qualifiers_cannot_escape_scope_without_mission_label(self):
        quote = "Em 11 de maio de 2001, o foguete Saturn V lançou a espaçonave Aster IX."
        for claim in (quote[:-1] + " tripulada.", quote[:-1] + " com quatro astronautas.",
                      quote.replace("lançou a", "lançou com sucesso a")):
            with self.subTest(claim=claim):
                self.assertTrue(is_launch_date_claim(claim))
                self.assertIsNone(launch_date_relation(claim, quote))
                self.assertIsNotNone(_passage_guard(claim, {"quote": quote, "context": quote}, "supports", STAMP))
        self.assertEqual(launch_date_relation(quote, quote), "supports")
        self.assertIsNone(_passage_guard(quote, {"quote": quote, "context": quote}, "supports", STAMP))

    def test_future_rocket_without_mission_label_cannot_use_generic_historical_present(self):
        for quote in ("The Saturn V rocket launches on May 11, 2030.",
                      "The Aster IX spacecraft launches on May 11, 2030."):
            with self.subTest(quote=quote):
                self.assertTrue(is_launch_date_claim(quote))
                self.assertIsNone(launch_date_relation(quote, quote))
                self.assertIsNotNone(_passage_guard(quote, {"quote": quote, "context": quote}, "supports", STAMP))


if __name__ == "__main__":
    unittest.main()
