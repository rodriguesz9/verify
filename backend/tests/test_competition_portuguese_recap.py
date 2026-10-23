"""Closed Portuguese BODY recaps, with invented results and no provider calls."""
import unittest

from app.services.competition_relations import competition_outcome_relation, parse_competition_claim
from app.services.source_corroboration import _prepare_sources, _passage_guard


CLAIM = "O Zeta venceu a Copa do Mundo de futebol masculino de 1903."
QUOTE = ("Com gol de Sola Nova no segundo tempo da prorrogação, "
         "os alemães conquistaram a Copa do Mundo 1903.")
STAMP = "2026-10-22T12:00:00+00:00"


class PortugueseCompetitionRecapTests(unittest.TestCase):
    def test_complete_recap_binds_team_demonym_competition_and_edition(self):
        for demonym, team in (("alemães", "Alemanha"), ("brasileiros", "Brasil"),
                              ("franceses", "França"), ("espanhóis", "Espanha"),
                              ("japoneses", "Japão"), ("sul-coreanos", "Coreia do Sul")):
            for year in ("1903", "1907"):
                with self.subTest(demonym=demonym, year=year):
                    quote = QUOTE.replace("alemães", demonym).replace("1903", year)
                    claim = CLAIM.replace("1903", year)
                    self.assertEqual(competition_outcome_relation(claim, quote), "refutes")
                    self.assertEqual(competition_outcome_relation(claim.replace("Zeta", team), quote), "supports")
                    self.assertIsNone(competition_outcome_relation(CLAIM.replace("1903", "1911"), quote))

    def test_only_closed_named_goal_and_completed_title_assertion_are_accepted(self):
        for period in ("primeiro tempo", "segundo tempo", "primeiro tempo da prorrogação",
                       "segundo tempo da prorrogação"):
            with self.subTest(period=period):
                self.assertEqual(competition_outcome_relation(CLAIM,
                    QUOTE.replace("segundo tempo da prorrogação", period)), "refutes")
        self.assertIsNone(parse_competition_claim(QUOTE))
        for quote in (QUOTE.replace("Sola Nova", "alguém"),
                      QUOTE.replace("Sola Nova", "brasil"),
                      QUOTE.replace("Sola Nova", "Sola e Nova"),
                      QUOTE.replace("alemães", "zetanos"),
                      QUOTE.replace("alemães", "alemães e brasileiros"),
                      QUOTE.replace("alemães", "alemães ou brasileiros"),
                      QUOTE.replace("conquistaram", "conquistarão"),
                      QUOTE.replace("conquistaram", "não conquistaram"),
                      QUOTE.replace("conquistaram", "teriam conquistado"),
                      QUOTE.replace("conquistaram", "conquistaram parcialmente")):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_unrecognized_prefix_or_suffix_cannot_be_silently_dropped(self):
        for quote in ("Segundo um jornalista, " + QUOTE,
                      "Em outra edição, " + QUOTE,
                      QUOTE + " O Zeta venceu outra edição.",
                      QUOTE[:-1] + " no torneio seguinte.",
                      QUOTE[:-1] + " em 1907.",
                      QUOTE[:-1] + " e conquistaram outro título.",
                      QUOTE[:-1] + " ou perderam outra final.",
                      QUOTE.replace("no segundo tempo da prorrogação", "na final estadual")):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))
        self.assertIsNone(competition_outcome_relation(CLAIM + " Foi invicto.", QUOTE))

    def test_other_tournaments_categories_fiction_and_context_still_veto(self):
        for competition in ("Copa regional 1903", "Mundial de clubes 1903", "Copa do Mundo feminina 1903",
                            "Copa do Mundo sub-20 1903", "Copa do Mundo de veteranos 1903",
                            "Copa do Mundo de futsal 1903", "Copa do Mundo 1907"):
            with self.subTest(competition=competition):
                self.assertIsNone(competition_outcome_relation(CLAIM,
                    QUOTE.replace("Copa do Mundo 1903", competition)))
        for context in ("Copa do Mundo feminina.", "Torneio de veteranos.", "Competição amadora.",
                        "É ficção.", "Relato fictício.", "Uma história inventada.",
                        "Uma simulação.", "Uma hipótese.", "Não ocorreu.", "É falso."):
            with self.subTest(context=context):
                self.assertIsNone(competition_outcome_relation(CLAIM, QUOTE, context + " " + QUOTE))
        self.assertIsNone(competition_outcome_relation(CLAIM, '"' + QUOTE + '"'))

    def test_body_role_context_retrieval_date_and_family_guards_remain(self):
        doc = {"url": "https://g1.globo.com/esporte/controle", "title": "Invented control",
               "sentences": [QUOTE], "sentence_roles": ["body"], "retrieved_at": STAMP, "truncated": False}
        sources, passages, _, _ = _prepare_sources([doc], [CLAIM], None)
        self.assertEqual([source["publisher_family"] for source in sources], ["globo"])
        self.assertEqual(len(passages), 1)
        passage = next(iter(passages.values()))
        self.assertIsNone(_passage_guard(CLAIM, passage, "refutes", STAMP))
        self.assertIsNotNone(_passage_guard(CLAIM, {**passage, "context": "Ao contrário, o resultado foi outro. " + QUOTE},
                                          "refutes", STAMP))
        for changed in ({**doc, "sentence_roles": ["context"]},
                        {**doc, "sentences": [QUOTE.replace("1903", "2093")]}):
            claim = CLAIM.replace("1903", "2093") if "2093" in changed["sentences"][0] else CLAIM
            self.assertEqual(_prepare_sources([changed], [claim], None)[0], [])


if __name__ == "__main__":
    unittest.main()
