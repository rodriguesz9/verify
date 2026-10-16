"""Explicit relation safeguards, invented controls, no network or accuracy claim."""
import unittest

from app.services.source_relations import lexical_text, opposing_directions, percentage_transition, opposing_measurements
from app.services.source_corroboration import _relation_guard, _same_event

DATE = "2026-10-16T12:00:00+00:00"


class SourceRelationTests(unittest.TestCase):
    def test_organization_aliases_preserve_identity(self):
        self.assertEqual(lexical_text("Organização Mundial da Saúde e WHO e OMS"), "WHO e WHO e WHO")
        self.assertEqual(lexical_text("Instituto Brasileiro de Geografia e Estatística"), "IBGE")
        self.assertNotEqual(lexical_text("Organização Mundial do Comércio"), "WHO")

    def test_abbreviation_and_predicate_paraphrase_can_match_without_changing_date(self):
        claim = "Em 11 de março de 2020, a Organização Mundial da Saúde caracterizou a COVID-19 como uma pandemia."
        quote = "A OMS classificou a COVID-19 como pandemia em 11 de março de 2020."
        self.assertTrue(_same_event(claim, quote))
        self.assertIsNone(_relation_guard(claim, quote, quote, "supports", DATE))
        self.assertIsNotNone(_relation_guard(claim.replace("2020", "2021"), quote, quote, "supports", DATE))

    def test_opposing_actions_refute_and_never_support_same_event(self):
        claim = "O Conselho Alfa reduziu a taxa Beta de 7,25% para 6,50% em 12 de agosto de 2021."
        quote = "O Conselho Alfa elevou a taxa Beta de 6,50% para 7,25% em 12 de agosto de 2021."
        self.assertTrue(opposing_directions(claim, quote))
        self.assertEqual(percentage_transition(claim), percentage_transition(quote)[::-1])
        self.assertIsNone(_relation_guard(claim, quote, quote, "refutes", DATE))
        self.assertIsNotNone(_relation_guard(claim, quote, quote, "supports", DATE))
        for changed in (quote.replace("12 de agosto", "13 de agosto"), quote.replace("7,25", "9,25"), quote.replace("Alfa", "Zeta")):
            self.assertIsNotNone(_relation_guard(claim, changed, changed, "refutes", DATE))

    def test_same_number_set_cannot_hide_reversed_transition(self):
        claim = "O Conselho Alfa alterou a taxa Beta de 7,25% para 6,50% em 2021."
        quote = "O Conselho Alfa alterou a taxa Beta de 6,50% para 7,25% em 2021."
        self.assertIsNotNone(_relation_guard(claim, quote, quote, "supports", DATE))
        self.assertIsNone(_relation_guard(claim, quote, quote, "refutes", DATE))

    def test_multiple_changes_or_bare_numbers_are_not_an_explicit_transition(self):
        for text in ("7,25 e 6,50", "de 7,25 para 6,50", "de 7% para 6%, depois de 6% para 5%"):
            self.assertIsNone(percentage_transition(text))
        self.assertFalse(opposing_directions("A taxa subiu ou caiu.", "A taxa reduziu."))

    def test_measured_opposition_preserves_value_unit_and_baseline(self):
        claim = "A medição Alfa ficou 1,60°C abaixo da média de 1850–1900 em 2024."
        quote = "A medição Alfa ficou 1.60 degrees Celsius above the average de 1850–1900 em 2024."
        self.assertTrue(opposing_measurements(claim, quote))
        self.assertIsNone(_relation_guard(claim, quote, quote, "refutes", DATE))
        self.assertIsNotNone(_relation_guard(claim, quote, quote, "supports", DATE))
        for other in (quote.replace("1.60", "1.70"), quote.replace("Celsius", "Fahrenheit"),
                      quote.replace("1850", "1860"), quote + " Outro índice ficou 2°C below a média."):
            self.assertIsNotNone(_relation_guard(claim, other, other, "refutes", DATE))

    def test_unbound_opposing_verbs_do_not_become_refutation(self):
        claim = "A empresa Alfa aumentou a taxa Beta em 2021."
        quote = "A empresa Alfa reduziu a taxa Beta em 2021."
        self.assertIsNotNone(_relation_guard(claim, quote, quote, "refutes", DATE))

    def test_calendar_may_is_not_modal_but_real_uncertainty_is_preserved(self):
        claim = "A nave Zeta colidiu com o asteroide Delta em 12 de maio de 2021."
        quote = "A nave Zeta colidiu com o asteroide Delta on May 12, 2021."
        self.assertIsNone(_relation_guard(claim, quote, quote, "supports", DATE))
        conditional = quote.replace("colidiu", "may ter colidido")
        self.assertIsNotNone(_relation_guard(claim, conditional, conditional, "supports", DATE))

    def test_year_claim_can_use_complete_event_date_but_not_money_or_another_year(self):
        claim = "A pesquisadora Zeta morreu em 2021."
        quote = "A pesquisadora Zeta morreu em 12 de agosto de 2021."
        self.assertIsNone(_relation_guard(claim, quote, quote, "supports", DATE))
        self.assertIsNone(_relation_guard(claim, claim, claim, "supports", DATE))
        self.assertIsNotNone(_relation_guard(claim.replace("2021", "2020"), quote, quote, "supports", DATE))
        monetary = "A pesquisadora Zeta recebeu R$ 2021."
        dated = "A pesquisadora Zeta recebeu R$ 12 em 12 de agosto de 2021."
        self.assertIsNotNone(_relation_guard(monetary, dated, dated, "supports", DATE))

    def test_partial_year_does_not_refute_full_date_within_the_same_year(self):
        claim = "A pesquisadora Zeta morreu em 12 de agosto de 2021."
        partial = "A pesquisadora Zeta morreu em 2021."
        self.assertIsNotNone(_relation_guard(claim, partial, partial, "refutes", DATE))
        self.assertIsNotNone(_relation_guard(claim, partial, partial, "supports", DATE))

    def test_new_impact_vocabulary_does_not_approve_a_future_completed_event(self):
        claim = "A nave Zeta colidiu com o asteroide Delta em 12 de agosto de 2027."
        self.assertIsNotNone(_relation_guard(claim, claim, claim, "supports", DATE))
