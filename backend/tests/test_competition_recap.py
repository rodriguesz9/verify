"""Offline closed-form recap controls, never stored sporting answers."""
import unittest

from app.services.competition_relations import competition_outcome_relation, parse_competition_claim


CLAIM = "O Zeta venceu a Copa do Mundo de futebol masculino de 2001."
RECAP = ("Omega win the 2001 Fifa World Cup thanks to Sola Nova's superb extra-time winner "
         "against Zeta at the Arena Nacional in Rio de Janeiro.")


class CompetitionRecapTests(unittest.TestCase):
    def test_present_recap_has_explicit_winner_competition_and_edition(self):
        for verb in ("win", "wins", "won", "has won"):
            quote = RECAP.replace(" win ", " " + verb + " ")
            self.assertEqual(competition_outcome_relation(CLAIM, quote), "refutes")
            self.assertEqual(competition_outcome_relation(CLAIM.replace("Zeta", "Omega"), quote), "supports")
            self.assertIsNone(competition_outcome_relation(CLAIM.replace("2001", "2002"), quote))

    def test_quote_only_recap_never_rewrites_claim_qualifiers(self):
        self.assertIsNone(parse_competition_claim(RECAP))
        self.assertIsNone(competition_outcome_relation(CLAIM + " Foi invicto.", RECAP))
        self.assertIsNone(competition_outcome_relation(CLAIM.replace("Zeta", "Zeta invicto"), RECAP))

    def test_captured_literal_english_recap_without_historical_answer_lookup(self):
        quote = ("Germany win the 2014 Fifa World Cup thanks to Mario Gotze's superb extra-time winner "
                 "against Argentina at the Maracana in Rio de Janeiro.")
        self.assertEqual(competition_outcome_relation(CLAIM.replace("2001", "2014"), quote), "refutes")
        self.assertEqual(competition_outcome_relation(CLAIM.replace("2001", "2014").replace("Zeta", "Alemanha"), quote), "supports")
        self.assertEqual(competition_outcome_relation(CLAIM, RECAP.replace("'", "’")), "refutes")

    def test_no_final_score_or_other_trophy_can_replace_title_assertion(self):
        for quote in (RECAP.replace("win the 2001 Fifa World Cup", "win the final"),
                      RECAP.replace("Fifa World Cup", "World Cup"),
                      RECAP.replace("Fifa World Cup", "Fifa Club World Cup"),
                      RECAP.replace("winner", "winner of the next edition"),
                      RECAP.replace("win the 2001 Fifa World Cup", "beat Zeta 1-0")):
            self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_category_uncertainty_quotation_or_plan_still_veto(self):
        for quote in (RECAP.replace("Fifa", "Women's Fifa"),
                      RECAP.replace("Fifa", "U-20 Fifa"),
                      "Rumor: " + RECAP,
                      '"' + RECAP + '"',
                      RECAP.replace(" win ", " will win "),
                      RECAP.replace(" win ", " may win "),
                      RECAP.replace(" win ", " did not win ")):
            self.assertIsNone(competition_outcome_relation(CLAIM, quote))
        self.assertIsNone(competition_outcome_relation(CLAIM, RECAP, "Women's World Cup."))

    def test_entire_suffix_consumed_and_named_actor_cannot_switch(self):
        for quote in (RECAP + " Another edition was won by Zeta.",
                      RECAP[:-1] + " but Zeta won another title.",
                      RECAP.replace("Omega win", "Omega and Zeta win"),
                      RECAP.replace("against Zeta", "against Omega"),
                      RECAP.replace("Sola Nova's", "someone's"),
                      RECAP.replace("at the Arena Nacional", "at another final"),
                      RECAP.replace("against Zeta", "against they")):
            self.assertIsNone(competition_outcome_relation(CLAIM, quote))


if __name__ == "__main__":
    unittest.main()
