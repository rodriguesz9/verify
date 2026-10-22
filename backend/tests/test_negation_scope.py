"""Invented controls: unrelated window negation cannot refute a named event."""
import unittest

from app.services.source_corroboration import _prepare_sources, _relation_guard


CLAIM = "O Instituto Zeta recebeu o Prêmio Delta em 2007."
STAMP = "2026-10-21T12:00:00+00:00"


def guard(claim, quote, relation="refutes"):
    return _relation_guard(claim, quote, quote, relation, STAMP)


class NegationScopeTests(unittest.TestCase):
    def test_complete_literal_statement_with_simple_negation_refutes_in_both_directions(self):
        for negation in ("não", "nao", "nunca", "jamais"):
            negative = CLAIM.replace("recebeu", negation + " recebeu")
            with self.subTest(negation=negation):
                self.assertIsNone(guard(CLAIM, negative))
                self.assertIsNone(guard(negative, CLAIM))
        english = "Institute Zeta has received Prize Delta."
        for negation in ("not", "never"):
            negative = english.replace("received", negation + " received")
            self.assertIsNone(guard(english, negative))
            self.assertIsNone(guard(negative, english))

    def test_case_whitespace_and_final_punctuation_do_not_change_statement_scope(self):
        negative = "  o instituto zeta NÃO   recebeu o prêmio delta em 2007.  "
        self.assertIsNone(guard(CLAIM, negative))

    def test_preceding_unrelated_negation_does_not_negate_following_event(self):
        quote = "Não era uma cerimônia comum. " + CLAIM
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_following_unrelated_negation_does_not_negate_preceding_event(self):
        quote = CLAIM + " O funcionário não viajou naquele mês."
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_negative_intention_of_another_actor_does_not_negate_completed_event(self):
        quote = CLAIM + " Os organizadores não tinham intenção de realizar a cerimônia."
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_denial_of_confirmation_is_not_denial_of_embedded_event(self):
        quote = "O Instituto Zeta não confirmou que recebeu o Prêmio Delta em 2007."
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_negative_statement_cannot_borrow_identity_from_other_sentence(self):
        quote = "O Instituto Zeta publicou seu relatório em 2007. Ele não recebeu o Prêmio Delta em 2007."
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_negative_statement_cannot_borrow_date_from_other_sentence(self):
        quote = "O Instituto Zeta não recebeu o Prêmio Delta. A cerimônia ocorreu em 2007."
        self.assertIsNotNone(guard(CLAIM, quote))

    def test_qualifiers_categories_entities_values_and_word_order_are_not_dropped(self):
        negative = CLAIM.replace("recebeu", "não recebeu")
        variants = (negative.replace("Prêmio Delta", "Prêmio Delta de ficção"),
                    negative.replace("Instituto Zeta", "Instituto Lambda"),
                    negative.replace("2007", "2008"),
                    "Em 2007, o Instituto Zeta não recebeu o Prêmio Delta.",
                    negative.replace("não recebeu", "não apenas recebeu"),
                    negative.replace("não recebeu", "nunca deixou de receber"))
        for quote in variants:
            with self.subTest(quote=quote):
                self.assertIsNotNone(guard(CLAIM, quote))

    def test_single_explicit_date_can_move_without_changing_event_or_polarity(self):
        claim = "O Instituto Zeta recebeu o Prêmio Delta em 12 de agosto de 2007."
        quote = "Em 12 de agosto de 2007, o Instituto Zeta não recebeu o Prêmio Delta."
        self.assertIsNone(guard(claim, quote))
        self.assertIsNone(guard(quote, claim))
        self.assertIsNotNone(guard(claim, quote.replace("12 de agosto", "13 de agosto")))
        self.assertIsNotNone(guard(claim, quote.replace("não recebeu", "não confirmou que recebeu")))

    def test_conflicting_literal_statements_in_one_window_are_not_categorical_denial(self):
        self.assertIsNotNone(guard(CLAIM, CLAIM + " " + CLAIM.replace("recebeu", "não recebeu")))

    def test_walking_scope_cannot_borrow_negation_from_another_place_in_window(self):
        claim = "O homem pisou na Lua."
        quote = "O homem pisou na Lua. O homem não pisou em Zeta."
        self.assertIsNotNone(guard(claim, quote))

    def test_walking_scope_cannot_negate_another_place_in_same_sentence(self):
        claim = "O homem pisou na Lua."
        quote = "O homem pisou na Lua, mas não pisou em Zeta."
        self.assertIsNotNone(guard(claim, quote))

    def test_complete_direct_opposite_can_remain_in_bounded_window(self):
        quote = "A cerimônia foi realizada no auditório. " + CLAIM.replace("recebeu", "não recebeu")
        self.assertIsNone(guard(CLAIM, quote))

    def test_existing_explicit_false_prefix_and_singleton_date_branches_remain_eligible(self):
        self.assertIsNone(guard(CLAIM, "É falso que " + CLAIM[0].lower() + CLAIM[1:]))
        self.assertIsNone(guard("Zeta morreu em 12 de agosto de 2007.", "Zeta morreu em 13 de agosto de 2007."))
        self.assertIsNone(guard(CLAIM, CLAIM, relation="supports"))

    def test_unrelated_negation_cannot_create_comparison_family(self):
        quote = "Não era uma cerimônia comum. " + CLAIM
        document = {"url": "https://www.bbc.com/portuguese/control", "sentences": [quote],
                    "sentence_roles": ["body"], "retrieved_at": STAMP}
        sources, passages, _, _ = _prepare_sources([document], [CLAIM], None)
        self.assertEqual(sources, [])
        self.assertEqual(passages, {})


if __name__ == "__main__":
    unittest.main()
