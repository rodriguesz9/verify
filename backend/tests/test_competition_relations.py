"""Offline literal sports-frame controls, not a historical-winner oracle."""
import unittest

from app.services.competition_relations import (
    competition_outcome_relation,
    is_competition_outcome_claim,
    parse_competition_claim,
)


CLAIM = "O Brasil venceu a Copa do Mundo de futebol masculino de 2014."
CNN_FINAL = ("Da CNN BrasilAdicionar CNN Brasil ao Há dez anos, o Maracanã era palco da grande decisão "
             "da Copa no Mundo de 2014, e fechava com chave de ouro um dos Mundiais mais vibrantes já presenciado pelos torcedores.")
CNN_WINNER = ("Na ocasião, a Alemanha venceu a Argentina por 1 a 0, com gol do jovem Mario Götze na prorrogação, "
              "e conquistou seu quarto título na história das Copas.")


class CompetitionRelationsTests(unittest.TestCase):
    def test_complete_literal_claim_has_typed_competition_edition_category_and_winner(self):
        frame = parse_competition_claim(CLAIM)
        self.assertEqual((frame.competition, frame.year, frame.category, frame.winner),
                         ("fifa-world-cup", 2014, "senior-men-national-association-football", "brasil"))

    def test_title_winner_is_read_from_literal_not_historical_memory(self):
        # Deliberately invented edition/winner. No real-world answer is used.
        claim = "A seleção de Zeta conquistou a Copa do Mundo de futebol masculino de 2097."
        self.assertEqual(competition_outcome_relation(claim, claim), "supports")
        self.assertEqual(competition_outcome_relation(claim, claim.replace("Zeta", "Omega")), "refutes")
        self.assertEqual(competition_outcome_relation(claim, claim.replace("2097", "2098")), None)

    def test_same_title_with_different_winner_refutes_even_without_claimed_team_in_quote(self):
        self.assertEqual(competition_outcome_relation(CLAIM, "A Alemanha foi campeã da Copa do Mundo de 2014."), "refutes")
        self.assertEqual(competition_outcome_relation(CLAIM.replace("Brasil", "Alemanha"),
                         "A Alemanha foi campeã da Copa do Mundo de 2014."), "supports")

    def test_supported_assertion_forms_preserve_whole_claim(self):
        statements = (
            "O Brasil ganhou a Copa do Mundo de 2014.",
            "O Brasil conquistou a taça da Copa do Mundo de 2014.",
            "O Brasil foi campeão da Copa do Mundo de 2014.",
            "A Copa do Mundo de 2014 foi vencida pelo Brasil.",
            "O campeão da Copa do Mundo de 2014 foi o Brasil.",
            "Brazil won the 2014 FIFA World Cup.",
            "Brazil were crowned champions of the 2014 men's football World Cup.",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                self.assertEqual(competition_outcome_relation(CLAIM, statement), "supports")

    def test_captured_cnn_body_window_binds_edition_and_explicit_title_winner(self):
        quote = CNN_FINAL + " " + CNN_WINNER
        self.assertEqual(competition_outcome_relation(CLAIM, quote), "refutes")
        self.assertEqual(competition_outcome_relation(CLAIM.replace("Brasil", "Alemanha"), quote), "supports")
        self.assertEqual(competition_outcome_relation(CLAIM.replace("2014", "2018"), quote), None)

    def test_generic_final_context_and_winner_sentence_alone_both_abstain(self):
        for quote in (CNN_FINAL, CNN_WINNER,
                      "Argentina e Alemanha disputaram a final da Copa do Mundo de 2014.",
                      "A final ocorreu no dia 13 de julho, no Rio de Janeiro, com Alemanha e Argentina."):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_context_never_supplies_missing_competition_year_or_winner(self):
        self.assertIsNone(competition_outcome_relation(CLAIM, CNN_WINNER, CNN_FINAL))
        self.assertIsNone(competition_outcome_relation(CLAIM, CNN_FINAL, CNN_WINNER))
        self.assertIsNone(competition_outcome_relation(CLAIM,
                          "A Alemanha foi campeã da Copa do Mundo.", "A edição foi em 2014."))

    def test_portuguese_competition_convention_requires_no_category_conflicts(self):
        self.assertEqual(competition_outcome_relation(CLAIM, "O Brasil venceu a Copa do Mundo de 2014."), "supports")
        for qualifier in ("feminina", "futebol feminino", "sub-20", "sub 17", "juvenil", "de base",
                          "de clubes", "de futsal", "de futebol de praia", "de rugby", "de cricket",
                          "de futebol de botão", "de videogame", "de futebol de rua", "de cegos",
                          "de futebol americano", "de tênis", "de golfe"):
            with self.subTest(qualifier=qualifier):
                quote = "O Brasil venceu a Copa do Mundo " + qualifier + " de 2014."
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))
                self.assertIsNone(competition_outcome_relation(CLAIM, CNN_FINAL + " " + CNN_WINNER,
                                  "Esta reportagem trata da Copa do Mundo " + qualifier + "."))

    def test_english_bare_world_cup_has_no_mens_football_default(self):
        for quote in ("Brazil won the 2014 World Cup.", "Brazil won the 2014 football World Cup.",
                      "Brazil won the 2014 men's World Cup.", "Brazil won the 2014 Women's FIFA World Cup.",
                      "Brazil won the 2014 U-20 FIFA World Cup.", "Brazil won the 2014 club FIFA World Cup.",
                      "Brazil won the 2014 futsal World Cup."):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_claim_suffixes_and_compound_assertions_cannot_be_silently_dropped(self):
        for claim in (CLAIM[:-1] + " invicto.", CLAIM[:-1] + " por 2 a 0.",
                      CLAIM[:-1] + " na final contra a Argentina.", CLAIM[:-1] + " no Maracanã.",
                      CLAIM[:-1] + " e Neymar foi o artilheiro.",
                      "Segundo um jornalista, " + CLAIM,
                      "Em 2014, o Brasil venceu a Copa do Mundo de futebol masculino."):
            with self.subTest(claim=claim):
                self.assertTrue(is_competition_outcome_claim(claim))
                self.assertIsNone(parse_competition_claim(claim))
                self.assertIsNone(competition_outcome_relation(claim, CNN_FINAL + " " + CNN_WINNER))

    def test_scope_guard_retains_unsupported_categories_but_not_unrelated_claims(self):
        for claim in ("O Brasil foi campeão da Copa do Mundo feminina de 2014.",
                      "O Brasil não venceu a Copa do Mundo de 2014.",
                      "Brazil won the 2014 World Cup.",
                      "O Brasil levou o título da Copa do Mundo de 2014.",
                      "O título da Copa do Mundo de 2014 ficou com o Brasil.",
                      "Brasil vence a Copa do Mundo de 2014.",
                      "Brazil wins the 2014 FIFA World Cup."):
            self.assertTrue(is_competition_outcome_claim(claim))
            self.assertIsNone(parse_competition_claim(claim))
        for claim in ("O Brasil sediou a Copa do Mundo de 2014.", "O Brasil venceu uma partida.", None, {}):
            self.assertFalse(is_competition_outcome_claim(claim))

    def test_other_finalists_runner_up_and_third_place_are_not_title_evidence(self):
        quotes = (
            "A Argentina e o Brasil foram finalistas da Copa do Mundo de 2014.",
            "A Argentina foi vice-campeã da Copa do Mundo de 2014.",
            "O Brasil foi o terceiro colocado da Copa do Mundo de 2014.",
            "A final da Copa do Mundo de 2014 reuniu Zeta e Omega. A Alemanha venceu uma partida e conquistou o título.",
            "A semifinal da Copa do Mundo de 2014 foi disputada no Brasil. " + CNN_WINNER,
            "A Copa do Mundo de 2014 teve fase de grupos. O Brasil venceu a Argentina por 1 a 0 e conquistou o título.",
        )
        for quote in quotes:
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_a_match_score_or_a_goal_is_not_a_literal_title_assertion(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã. "
        for result in ("A Alemanha venceu a Argentina por 1 a 0.", "Mario Götze marcou o gol da vitória.",
                       "Alemanha 1x0 Argentina.", "O Brasil venceu a Croácia por 3 a 1."):
            with self.subTest(result=result):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + result))

    def test_rumor_prediction_denial_and_quoted_false_statement_abstain(self):
        for prefix in ("Segundo um boato, ", "Supostamente, ", "A previsão afirma que ", "É falso que ",
                       "Um jornalista disse que ", "An analyst said that ", '"', "Não é verdade que "):
            with self.subTest(prefix=prefix):
                self.assertIsNone(competition_outcome_relation(CLAIM, prefix + "O Brasil venceu a Copa do Mundo de 2014."))
                self.assertIsNone(competition_outcome_relation(CLAIM, CNN_FINAL + " " + CNN_WINNER,
                                  prefix + "a declaração anterior foi divulgada."))
        for quote in ("O Brasil poderia vencer a Copa do Mundo de 2014.",
                      "O Brasil será campeão da Copa do Mundo de 2014.",
                      "O Brasil não venceu a Copa do Mundo de 2014."):
            self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_edition_cannot_be_borrowed_from_a_different_competition(self):
        for quote in ("A final da Copa do Mundo de 2018 ocorreu no Brasil. " + CNN_WINNER,
                      CNN_FINAL + " A Alemanha venceu a Copa do Mundo de 2018.",
                      "A Copa do Mundo de 2014 ocorreu no Brasil. A final da Copa do Mundo de 2018 foi emocionante. " + CNN_WINNER):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_up_to_three_body_sentences_can_carry_one_complete_title_frame(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã."
        preceding = "O público acompanhou a partida."
        self.assertEqual(competition_outcome_relation(CLAIM, preceding + " " + anchor + " " + CNN_WINNER), "refutes")
        self.assertIsNone(competition_outcome_relation(CLAIM, preceding + " A noite foi longa. " + anchor + " " + CNN_WINNER))

    def test_intermediate_sentence_cannot_introduce_an_untyped_new_final_or_edition(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã. "
        winner = " A França venceu a Croácia por 4 a 2 e conquistou o título."
        for intermediate in ("Na edição seguinte, a decisão foi em Paris.",
                             "Houve outra final em Paris.",
                             "A decisão estadual aconteceu em Paris.",
                             "O público acompanhou a prorrogação."):
            with self.subTest(intermediate=intermediate):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + intermediate + winner))

    def test_anchor_sentence_cannot_switch_edition_decision_or_subject(self):
        winner = " A França venceu a Croácia por 4 a 2 e conquistou o título."
        for anchor in (
            "A final da Copa do Mundo de 2014 antecedeu a edição seguinte, cuja decisão ocorreu em Paris.",
            "A final da Copa do Mundo de 2014 ficou para trás; a edição seguinte terminou em Paris.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã, mas outra decisão aconteceu em Paris.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã e a França jogou outra decisão.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã, cuja decisão posterior ocorreu em Paris.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã; outra partida terminou em Paris.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã em outra edição.",
            "The final of the 2014 FIFA World Cup preceded another edition, whose final was in Paris.",
            "The final of the 2014 FIFA World Cup happened in Zeta; the later final was in Paris.",
        ):
            with self.subTest(anchor=anchor):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + winner))

    def test_clean_narrative_anchor_and_literal_captured_cnn_both_remain_bound(self):
        clean = "Há dez anos, o Maracanã era palco da grande decisão da Copa no Mundo de 2014."
        self.assertEqual(competition_outcome_relation(CLAIM, clean + " " + CNN_WINNER), "refutes")
        self.assertEqual(competition_outcome_relation(CLAIM, CNN_FINAL + " " + CNN_WINNER), "refutes")

    def test_stadium_arena_or_proper_venue_can_directly_govern_the_final(self):
        for prefix in ("O estádio foi", "A arena era", "O Maracanã foi", "Maracanã era", "A Arena Nacional foi"):
            anchor = prefix + " palco da grande decisão da Copa do Mundo de 2014."
            with self.subTest(prefix=prefix):
                self.assertEqual(competition_outcome_relation(CLAIM, anchor + " " + CNN_WINNER), "refutes")

    def test_venue_anchor_still_consumes_the_entire_subject_and_complement(self):
        for anchor in (
            "O estádio da edição seguinte foi palco da grande decisão da Copa do Mundo de 2014.",
            "A arena de outra decisão foi palco da grande decisão da Copa do Mundo de 2014.",
            "O Maracanã foi palco da grande decisão da Copa do Mundo de 2014, mas a edição posterior foi em Paris.",
            "O estádio foi palco da grande decisão da Copa do Mundo de 2014; outra decisão aconteceu em Paris.",
            "A arena foi palco da grande decisão da Copa do Mundo de 2014 e a decisão estadual foi em Paris.",
        ):
            with self.subTest(anchor=anchor):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + " " + CNN_WINNER))

    def test_ambiguous_or_unnamed_winner_abstains(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã. "
        for sentence in ("Ela venceu a Argentina por 1 a 0 e conquistou o título.",
                         "Alemanha ou Argentina venceu e conquistou o título.",
                         "A Alemanha e a Argentina conquistaram o título.",
                         "A seleção ganhou a taça."):
            with self.subTest(sentence=sentence):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + sentence))

    def test_quoted_winner_is_never_repaired_or_extended_with_headline_text(self):
        self.assertIsNone(competition_outcome_relation(CLAIM, CNN_FINAL,
                          "A Alemanha conquistou o quarto título e o Brasil terminou em quarto."))
        self.assertIsNone(competition_outcome_relation(CLAIM, "A Alemanha venceu a Copa do Mundo de 2018.",
                          "Copa do Mundo de futebol masculino de 2014"))

    def test_title_actor_cannot_change_after_match_winner(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã. "
        for sentence in (
            "A Alemanha venceu a Argentina por 1 a 0, mas o Uruguai conquistou o título.",
            "A Alemanha venceu a Argentina por 1 a 0 e o Uruguai conquistou o título.",
            "A Alemanha venceu a Argentina por 1 a 0, o Uruguai jogou melhor e conquistou o título.",
            "A Alemanha venceu a Argentina por 1 a 0 e o Uruguai venceu o Brasil e conquistou o título.",
            "O Brasil venceu a Argentina por 1 a 0, com gol de Zeta que brilhou e conquistou o título.",
            "O Brasil venceu a Argentina por 1 a 0, com gol de Zeta e Omega e conquistou o título.",
            "Germany beat Argentina 1-0; Uruguay played well and won the title.",
            "Germany beat Argentina 1-0, and Uruguay won the title.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + sentence))

    def test_title_suffix_cannot_name_another_prize_tournament_or_edition(self):
        anchor = "A final da Copa do Mundo de 2014 aconteceu no Maracanã. "
        for suffix in ("do Campeonato Paulista", "de melhor ataque", "na edição seguinte", "em sonho", "— isso é mentira"):
            quote = anchor + "O Brasil venceu a Argentina por 1 a 0 e conquistou o título " + suffix + "."
            with self.subTest(suffix=suffix):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_qualifiers_cannot_be_absorbed_into_literal_winner_identity(self):
        for claim in ("O Brasil invicto venceu a Copa do Mundo de 2014.",
                      "O Brasil novamente venceu a Copa do Mundo de 2014.",
                      "O Brasil obviamente venceu a Copa do Mundo de 2014.",
                      "The undefeated Brazil won the 2014 FIFA World Cup.",
                      "A seleção amadora do Brasil venceu a Copa do Mundo de 2014.",
                      "O campeão da Copa do Mundo de 2014 foi o Brasil invicto."):
            with self.subTest(claim=claim):
                self.assertTrue(is_competition_outcome_claim(claim))
                self.assertIsNone(parse_competition_claim(claim))
                self.assertIsNone(competition_outcome_relation(claim, CLAIM))

    def test_another_tournaments_final_cannot_own_world_cup_title(self):
        for quote in (
            "A final da Copa América sucedeu a Copa do Mundo de 2014. O Brasil venceu a Argentina por 1 a 0 e conquistou o título.",
            "Depois da Copa do Mundo de 2014, veio a Copa América. O Brasil foi campeão do torneio.",
            "A final da Copa do Mundo de 2014 aconteceu depois da Copa América. O Brasil venceu a Argentina por 1 a 0 e conquistou o título.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã. A Copa América teve sua própria final. O Brasil venceu a Argentina por 1 a 0 e conquistou o título.",
            "A final da Copa do Mundo de 2014 aconteceu no Maracanã. Outro torneio terminou em Buenos Aires. O Brasil foi campeão do torneio.",
        ):
            with self.subTest(quote=quote):
                self.assertIsNone(competition_outcome_relation(CLAIM, quote))

    def test_named_finalists_must_match_both_named_participants(self):
        winner = " O Brasil venceu a Argentina por 1 a 0 e conquistou o título."
        for anchor in (
            "A final da Copa do Mundo de 2014 reuniu Brasil e Alemanha.",
            "Brasil e Alemanha disputaram a final da Copa do Mundo de 2014.",
            "A final da Copa do Mundo de 2014 foi Argentina contra Alemanha.",
            "A final da Copa do Mundo de 2014 opôs Alemanha e Argentina.",
            "A final da Copa do Mundo de 2014 teve Alemanha e Argentina.",
            "A final da Copa do Mundo de 2014 reuniu Alemanha e Argentina, no Maracanã.",
            "A final da Copa do Mundo de 2014 foi entre Alemanha e Argentina, no Maracanã.",
        ):
            with self.subTest(anchor=anchor):
                self.assertIsNone(competition_outcome_relation(CLAIM, anchor + winner))
        valid = "A final da Copa do Mundo de 2014 reuniu Brasil e Argentina." + winner
        self.assertEqual(competition_outcome_relation(CLAIM, valid), "supports")

    def test_english_football_final_window_requires_explicit_named_title_winner(self):
        claim = "Brazil won the 2097 FIFA World Cup."
        anchor = "The final of the 2097 FIFA World Cup happened in Zeta. "
        self.assertEqual(competition_outcome_relation(claim,
                         anchor + "Brazil beat Argentina 1-0 and won the title."), "supports")
        self.assertEqual(competition_outcome_relation(claim,
                         anchor + "France defeated Argentina 1-0 and won the title."), "refutes")
        self.assertIsNone(competition_outcome_relation(claim,
                          anchor + "Brazil beat Argentina 1-0 and Uruguay won the title."))


if __name__ == "__main__":
    unittest.main()
