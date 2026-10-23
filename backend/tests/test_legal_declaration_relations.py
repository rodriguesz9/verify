"""Complete literal declarations; no model, lookup, source trust or verdict."""
import unittest

from app.services.legal_declaration_relations import (
    legal_declaration_relation, parse_legal_article_declaration, parse_legal_declaration_claim,
    legal_declaration_has_unsafe_scope,
)


REFERENCE = "Lei nº 8.541, de 15 de abril de 2010"
CLAIM = f"O artigo 7º da {REFERENCE}, declarou legalmente extinta a taxa no Município Zeta."
QUOTE = "Art. 7º É declarada extinta a taxa no Município Zeta."
ANCHOR = {"kind": "explicit_numbered_legal_article", "law_number": "8541", "law_date": "2010-04-15",
          "article_number": "7", "reference": REFERENCE}


class LegalDeclarationRelationTests(unittest.TestCase):
    def relation(self, claim=CLAIM, quote=QUOTE, anchor=None):
        return legal_declaration_relation(claim, quote, ANCHOR if anchor is None else anchor)

    def test_complete_positive_and_one_outer_negative_declaration(self):
        self.assertEqual(self.relation(), "supports")
        self.assertEqual(self.relation(CLAIM.replace("declarou", "não declarou")), "refutes")
        parsed = parse_legal_declaration_claim(CLAIM)
        self.assertEqual((parsed.law_number, parsed.law_date, parsed.article_number), ("8541", "2010-04-15", "7"))
        self.assertFalse(parsed.negative)
        self.assertEqual(parsed.payload, "extinta a taxa no município zeta")

    def test_closed_reflexive_declaration_preserves_whole_payload(self):
        quote = QUOTE.replace("É declarada", "Declara-se")
        self.assertEqual(self.relation(quote=quote), "supports")
        self.assertEqual(self.relation(CLAIM.replace("declarou", "não declarou"), quote), "refutes")
        self.assertIsNone(self.relation(quote=quote[:-1] + " apenas para moradores isentos."))

    def test_unknown_unconditional_style_is_not_itself_a_scope_veto_or_literal_vote(self):
        quote = QUOTE.replace("É declarada", "É pelo presente artigo declarada")
        self.assertIsNone(parse_legal_article_declaration(quote))
        self.assertIsNone(self.relation(quote=quote))
        self.assertFalse(legal_declaration_has_unsafe_scope(quote))
        for tail in (" caso haja autorização", " apenas para moradores isentos", ", salvo autorização", " e não a tarifa"):
            self.assertTrue(legal_declaration_has_unsafe_scope(quote[:-1] + tail + "."))

    def test_other_law_article_and_object_use_same_generic_contract(self):
        reference = "Lei n° 12.345, de 29 de fevereiro de 2020"
        claim = f"O artigo 12 da {reference}, declarou extinto o tributo no Distrito Boreal."
        quote = "Artigo 12 Foi declarado extinto o tributo no Distrito Boreal."
        anchor = {"kind": "explicit_numbered_legal_article", "law_number": "12345", "law_date": "2020-02-29",
                  "article_number": "12", "reference": reference}
        self.assertEqual(self.relation(claim, quote, anchor), "supports")

    def test_only_explicit_orthographic_aliases_are_normalized(self):
        claim = CLAIM.replace("no Município Zeta", "no Brasil")
        quote = QUOTE.replace("extinta", "extincta").replace("no Município Zeta", "no Brazil")
        self.assertEqual(self.relation(claim, quote), "supports")
        self.assertIsNone(self.relation(claim, quote.replace("extincta", "eliminada")))

    def test_closed_same_law_date_modifier_is_recorded(self):
        for bridge in ("desde a data desta Lei, ", "desde a data d'esta Lei, ", "desde a data d’esta Lei, "):
            quote = QUOTE.replace("extinta ", "extincta " + bridge)
            with self.subTest(bridge=bridge):
                self.assertEqual(self.relation(quote=quote), "supports")
                frame = parse_legal_article_declaration(quote)
                self.assertEqual(frame.effective_scope, "same_law_date")
                self.assertEqual(frame.payload, "extinta a taxa no município zeta")

    def test_numbered_body_forms_preserve_the_same_article_identity(self):
        for marker in ("Art.7°", "Artigo 7º", "7º", "7°"):
            quote = QUOTE.replace("Art. 7º", marker)
            with self.subTest(marker=marker):
                self.assertEqual(self.relation(quote=quote), "supports")
                self.assertEqual(parse_legal_article_declaration(quote).article_number, "7")
        for marker in ("7", "7o", "Art.", "8º"):
            self.assertIsNone(self.relation(quote=QUOTE.replace("Art. 7º", marker)))

    def test_comma_before_only_the_closed_same_law_date_bridge_is_accepted(self):
        for marker in ("Art.7°", "7º"):
            quote = QUOTE.replace("Art. 7º", marker).replace("extinta ", "extinta, desde a data desta Lei, ")
            with self.subTest(marker=marker):
                self.assertEqual(self.relation(quote=quote), "supports")
                self.assertEqual(parse_legal_article_declaration(quote).effective_scope, "same_law_date")
        for suffix in (", caso o conselho aprove", ", salvo autorização contrária", ", apenas para moradores isentos",
                       ", desde a data de outra Lei", ", desde a data desta Lei, salvo autorização"):
            self.assertIsNone(self.relation(quote=QUOTE.replace("extinta ", "extinta" + suffix + ", ")))

    def test_claimed_same_law_date_modifier_is_not_filled_from_undated_body(self):
        claim = CLAIM.replace("extinta ", "extinta desde a data desta Lei, ")
        self.assertIsNone(self.relation(claim))
        self.assertEqual(self.relation(claim, QUOTE.replace("extinta ", "extinta desde a data desta Lei, ")), "supports")

    def test_arbitrary_dates_and_temporal_modifiers_are_not_removed(self):
        for tail in ("desde a data de outra Lei, ", "desde 2021, ", "a partir de 2030, ", "até a data desta Lei, "):
            with self.subTest(tail=tail):
                self.assertIsNone(self.relation(quote=QUOTE.replace("extinta ", "extinta " + tail)))
        self.assertIsNone(self.relation(quote=QUOTE.replace("extinta", "eliminada desde a data desta Lei,")))

    def test_condition_exception_and_restriction_never_gain_literal_direction(self):
        for suffix in (", caso o conselho aprove", " se o conselho aprovar", " salvo autorização contrária",
                       " exceto para moradores isentos", " apenas para moradores isentos", " quando houver autorização"):
            with self.subTest(suffix=suffix):
                quote = QUOTE[:-1] + suffix + "."
                self.assertIsNone(self.relation(quote=quote))
                self.assertIsNone(self.relation(CLAIM.replace("declarou", "não declarou"), quote))
                self.assertIsNone(self.relation(CLAIM[:-1] + suffix + ".", quote))

    def test_payload_order_and_every_qualifier_are_preserved(self):
        for quote in (QUOTE.replace("taxa no Município Zeta", "taxa Zeta no Município"),
                      QUOTE.replace("taxa", "taxa anual"), QUOTE.replace("Zeta", "Beta"),
                      QUOTE.replace("taxa", "cobrança da taxa"), QUOTE[:-1] + " para moradores isentos."):
            with self.subTest(quote=quote):
                self.assertIsNone(self.relation(quote=quote))
        self.assertIsNone(self.relation(CLAIM.replace("taxa", "taxa anual")))

    def test_nested_negation_and_denial_of_another_event_are_not_collapsed(self):
        for claim in (CLAIM.replace("legalmente extinta", "legalmente não extinta"),
                      CLAIM.replace("declarou", "não não declarou"),
                      CLAIM[:-1] + " e não extinguiu a cobrança real.",
                      CLAIM.replace("declarou", "não informou que declarou")):
            with self.subTest(claim=claim):
                self.assertIsNone(self.relation(claim))
        for quote in (QUOTE.replace("É declarada", "Não é declarada"),
                      QUOTE[:-1] + " A cobrança não foi encerrada.",
                      QUOTE[:-1] + " e não é declarada extinta a tarifa."):
            self.assertIsNone(self.relation(quote=quote))

    def test_mismatched_article_law_number_or_law_date_is_unknown(self):
        for claim in (CLAIM.replace("7º", "8º"), CLAIM.replace("8.541", "8.542"),
                      CLAIM.replace("15 de abril", "16 de abril")):
            self.assertIsNone(self.relation(claim))
        self.assertIsNone(self.relation(quote=QUOTE.replace("7º", "8º")))

    def test_forged_or_internally_inconsistent_anchor_is_rejected(self):
        for field, value in (("kind", "model_inferred_article"), ("law_number", "8542"),
                             ("law_date", "2010-04-16"), ("article_number", "8"),
                             ("reference", REFERENCE.replace("8.541", "8.542")),
                             ("reference", "Uma notícia sobre " + REFERENCE)):
            with self.subTest(field=field, value=value):
                self.assertIsNone(self.relation(anchor={**ANCHOR, field: value}))
        self.assertIsNone(self.relation(anchor={key: value for key, value in ANCHOR.items() if key != "reference"}))
        self.assertIsNone(self.relation(anchor={**ANCHOR, "model_proof": True}))
        self.assertIsNone(self.relation(anchor={}))

    def test_invalid_calendar_identity_is_never_accepted(self):
        for date in ("31 de abril de 2010", "29 de fevereiro de 2019", "0 de abril de 2010"):
            claim = CLAIM.replace("15 de abril de 2010", date)
            self.assertIsNone(parse_legal_declaration_claim(claim))
            self.assertIsNone(self.relation(claim))
        self.assertIsNone(self.relation(CLAIM.replace("artigo 7º", "artigo 0º")))

    def test_free_prefixes_suffixes_quotes_and_other_articles_do_not_fullmatch(self):
        for claim in ("Segundo o comentarista, " + CLAIM, CLAIM + " Continua em vigor.",
                      CLAIM[:-1] + "?", '"' + CLAIM + '"', CLAIM.replace("declarou", "teria declarado")):
            self.assertIsNone(parse_legal_declaration_claim(claim))
        for quote in ("O autor citou: " + QUOTE, QUOTE + " Art. 8º Fica extinta outra taxa.",
                      QUOTE[:-1] + "?", '"' + QUOTE + '"'):
            self.assertIsNone(parse_legal_article_declaration(quote))

    def test_case_whitespace_and_optional_final_period_do_not_change_payload(self):
        self.assertEqual(self.relation(CLAIM.upper().replace(" ", "  "), QUOTE.upper()[:-1]), "supports")

    def test_bad_input_types_and_excess_size_fall_back(self):
        for value in (None, {}, [], "", "x" * 1201):
            self.assertIsNone(parse_legal_declaration_claim(value))
            self.assertIsNone(parse_legal_article_declaration(value))
        self.assertIsNone(legal_declaration_relation(CLAIM, QUOTE, None))


if __name__ == "__main__":
    unittest.main()
