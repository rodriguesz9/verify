"""Closed official-record decision controls, not live factual accuracy."""
from copy import deepcopy
from decimal import Decimal
import unittest

from app.services.monetary_decisions import (
    copom_record_relation, parse_copom_claim, validate_copom_record,
)
from app.services.official_source_body import COPOM_INDEX_URL, COPOM_SCHEMA_URL


STAMP = "2024-09-18"
PROOF = {
    "kind": "bcb_copom_comunicado",
    "record_id": "265",
    "record_url": "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=265",
    "record_reference_date": STAMP,
    "reference_date_semantics": "bcb_comunicado_publication_reference_date",
    "schema_url": COPOM_SCHEMA_URL,
    "discovery_url": COPOM_INDEX_URL,
}
CLAIM = "Em 18 de setembro de 2024, o Copom elevou a Selic de 10,50% para 10,75% ao ano."
FORMAL = "O Copom decidiu, por unanimidade, elevar a taxa básica de juros em 0,25 ponto percentual, para 10,75% a.a."
CAPTURED_FORMAL = (
    "Considerando a evolução do processo de desinflação, os cenários avaliados, o balanço de riscos e o amplo "
    "conjunto de informações disponíveis, o Copom decidiu, por unanimidade, elevar a taxa básica de juros "
    "em 0,25 ponto percentual, para 10,75% a.a., e entende que essa decisão é compatível com a estratégia "
    "de convergência da inflação para o redor da meta ao longo do horizonte relevante."
)


class MonetaryDecisionRecordTests(unittest.TestCase):
    def test_claim_fields_are_typed_literal_not_rate_lookup(self):
        parsed = parse_copom_claim(CLAIM)
        self.assertEqual(parsed.reference_date, STAMP)
        self.assertEqual(parsed.action, "raise")
        self.assertEqual(parsed.previous, Decimal("10.50"))
        self.assertEqual(parsed.target, Decimal("10.75"))

    def test_generic_other_dates_meetings_and_rates_do_not_use_answer_tables(self):
        for stamp, number, old, new in (("1999-03-12", 77, "8.25", "9.00"),
                                       ("2031-05-19", 4999, "12.75", "12.50")):
            with self.subTest(stamp=stamp):
                proof = {**PROOF, "record_id": str(number), "record_reference_date": stamp,
                         "record_url": PROOF["record_url"].replace("265", str(number))}
                verb, infinitive = ("elevou", "elevar") if Decimal(old) < Decimal(new) else ("reduziu", "reduzir")
                claim = f"Em {stamp}, o Copom {verb} a taxa Selic de {old}% para {new}% ao ano."
                quote = f"O Copom decidiu {infinitive} a taxa Selic de {old}% para {new}% ao ano."
                self.assertTrue(validate_copom_record(proof))
                self.assertEqual(copom_record_relation(claim, quote, proof), "supports")
                # Pure relation deliberately leaves future-versus-retrieval validation to caller.

    def test_absolute_date_formats_but_no_relative_or_invalid_dates(self):
        for value in ("18/09/2024", "2024-09-18", "18 de setembro de 2024"):
            with self.subTest(value=value):
                self.assertEqual(parse_copom_claim(CLAIM.replace("18 de setembro de 2024", value)).reference_date, STAMP)
        for value in ("ontem", "hoje", "setembro de 2024", "18 de setembro", "31 de fevereiro de 2024", "2024-02-30"):
            with self.subTest(value=value):
                self.assertIsNone(parse_copom_claim(CLAIM.replace("18 de setembro de 2024", value)))

    def test_record_has_exact_canonical_provenance(self):
        self.assertTrue(validate_copom_record(PROOF))
        for key in PROOF:
            with self.subTest(key=key):
                missing = deepcopy(PROOF)
                missing.pop(key)
                self.assertFalse(validate_copom_record(missing))
        self.assertFalse(validate_copom_record({**PROOF, "headline": "Copom eleva Selic"}))
        for value in (None, "", [], True):
            self.assertFalse(validate_copom_record(value))

    def test_record_number_url_path_origin_and_parameters_cannot_change(self):
        for value in ("0", "5001", "0265", "265 ", "265&x=1", 265, True):
            with self.subTest(value=value):
                self.assertFalse(validate_copom_record({**PROOF, "record_id": value}))
        for value in (
            PROOF["record_url"].replace("265", "266"),
            "https://www.bcb.gov.br/detalhenoticia/265/nota",
            PROOF["record_url"] + "&download=1", PROOF["record_url"] + "#x",
            PROOF["record_url"].replace("www.bcb.gov.br", "www.bcb.gov.br.example.test"),
            PROOF["record_url"].replace("https:", "http:"),
            PROOF["record_url"].replace("265", "%32%36%35"),
        ):
            with self.subTest(value=value):
                bad = {**PROOF, "record_url": value}
                self.assertFalse(validate_copom_record(bad))
                self.assertIsNone(copom_record_relation(CLAIM, FORMAL, bad))

    def test_record_kind_schema_discovery_and_date_semantics_are_revalidated(self):
        for key, value in (("kind", "news_article"), ("schema_url", "https://example.test/copom.yaml"),
                           ("discovery_url", "https://www.bcb.gov.br/controleinflacao/comunicadoscopom"),
                           ("reference_date_semantics", "article_publication_date"),
                           ("reference_date_semantics", "meeting_timestamp"),
                           ("record_reference_date", "2024-02-30"),
                           ("record_reference_date", "2024-9-18"),
                           ("record_reference_date", STAMP + "T00:00:00Z")):
            with self.subTest(key=key, value=value):
                self.assertFalse(validate_copom_record({**PROOF, key: value}))

    def test_exact_record_date_required_not_nearest_record_or_publication_guess(self):
        self.assertIsNone(copom_record_relation(CLAIM, FORMAL, {**PROOF, "record_reference_date": "2024-09-19"}))
        self.assertIsNone(copom_record_relation(CLAIM.replace("2024", "2023"), FORMAL, PROOF))
        self.assertIsNone(copom_record_relation(CLAIM, FORMAL, {"publication_date": STAMP, "url": PROOF["record_url"]}))

    def test_full_captured_formal_decision_and_safe_rationale_are_consumed(self):
        self.assertEqual(copom_record_relation(CLAIM, CAPTURED_FORMAL, PROOF), "supports")
        self.assertEqual(copom_record_relation(CLAIM, CAPTURED_FORMAL.replace("o redor da meta", "a meta"), PROOF),
                         "supports")
        self.assertEqual(copom_record_relation(CLAIM,
            "O Comitê de Política Monetária (Copom) decidiu elevar a taxa Selic de 10,50% para 10,75% ao ano.", PROOF),
            "supports")

    def test_false_transition_refuted_by_same_formal_decision(self):
        false = "Em 18 de setembro de 2024, o Copom reduziu a Selic de 10,75% para 10,50% ao ano."
        self.assertEqual(copom_record_relation(false, CAPTURED_FORMAL, PROOF), "refutes")
        self.assertEqual(copom_record_relation(CLAIM.replace("10,75%", "11,00%"), FORMAL, PROOF), "refutes")

    def test_old_rate_needs_explicit_transition_or_one_percentage_point_delta(self):
        target_only = "O Copom decidiu elevar a Selic para 10,75% ao ano."
        self.assertIsNone(copom_record_relation(CLAIM, target_only, PROOF))
        self.assertEqual(copom_record_relation(CLAIM.replace("de 10,50% ", ""), target_only, PROOF), "supports")
        self.assertEqual(copom_record_relation(CLAIM, FORMAL, PROOF), "supports")
        self.assertEqual(copom_record_relation(CLAIM,
            "O Copom decidiu elevar a Selic de 10,25% para 10,75% ao ano.", PROOF), "refutes")

    def test_raise_lower_hold_actions_are_not_interchangeable(self):
        hold = "Em 18 de setembro de 2024, o Copom manteve a Selic em 10,75% ao ano."
        body = "O Copom decidiu manter a taxa Selic em 10,75% a.a."
        self.assertEqual(copom_record_relation(hold, body, PROOF), "supports")
        self.assertEqual(copom_record_relation(CLAIM, body, PROOF), "refutes")
        lower = "Em 18 de setembro de 2024, o Copom reduziu a Selic de 11,00% para 10,75% ao ano."
        self.assertEqual(copom_record_relation(lower, FORMAL.replace("elevar", "reduzir"), PROOF), "supports")
        self.assertEqual(copom_record_relation(lower, FORMAL, PROOF), "refutes")

    def test_percentage_points_not_percent_or_basis_point_guess(self):
        for delta in ("em 0,25%", "em 25 pontos-base", "em 0,25 ponto", "em 0,25 porcento",
                      "em zero vírgula vinte e cinco ponto percentual"):
            with self.subTest(delta=delta):
                quote = FORMAL.replace("em 0,25 ponto percentual", delta)
                self.assertIsNone(copom_record_relation(CLAIM, quote, PROOF))
        self.assertEqual(copom_record_relation(CLAIM, FORMAL.replace("0,25", "0.25"), PROOF), "supports")

    def test_unknown_annual_basis_other_measures_and_missing_unit_abstain(self):
        for old, new in (("a.a.", "ao mês"), ("a.a.", ""), ("10,75%", "10,75 pontos percentuais"),
                         ("taxa básica de juros", "taxa de câmbio"), ("Selic", "inflação")):
            body = FORMAL if old != "Selic" else FORMAL.replace("taxa básica de juros", "Selic")
            with self.subTest(change=(old, new)):
                self.assertIsNone(copom_record_relation(CLAIM, body.replace(old, new), PROOF))

    def test_inconsistent_claim_or_formal_action_values_abstain(self):
        for value in (CLAIM.replace("elevou", "reduziu"), CLAIM.replace("elevou", "manteve"),
                      CLAIM.replace("para 10,75%", "para 10,50%"),
                      CLAIM.replace("elevou", "aumentou em 0,25 ponto percentual e elevou")):
            with self.subTest(value=value):
                self.assertIsNone(parse_copom_claim(value))
        for value in (FORMAL.replace("0,25", "0,00"), FORMAL.replace("0,25", "20,00"),
                      FORMAL.replace("elevar", "manter"),
                      "O Copom decidiu reduzir a Selic de 10,50% para 10,75% ao ano."):
            with self.subTest(value=value):
                self.assertIsNone(copom_record_relation(CLAIM, value, PROOF))

    def test_unknown_subject_advice_negation_uncertainty_and_claim_qualifiers_abstain(self):
        for value in (
            CLAIM.replace("o Copom", "o Fed"), CLAIM.replace("elevou", "não elevou"),
            CLAIM.replace("elevou", "elevará"), CLAIM.replace("elevou", "teria elevado"),
            CLAIM[:-1] + " por unanimidade.", CLAIM[:-1] + " após cortar os juros.",
            CLAIM + " Invista agora.", CLAIM.replace("o Copom elevou", "você deve elevar"),
            '"' + CLAIM + '"', "Segundo uma mensagem, " + CLAIM,
        ):
            with self.subTest(value=value):
                self.assertIsNone(parse_copom_claim(value))
                self.assertIsNone(copom_record_relation(value, FORMAL, PROOF))

    def test_unknown_conditions_before_or_after_decision_cannot_be_trimmed(self):
        for value in (
            "Se a inflação cair, " + FORMAL,
            FORMAL[:-1] + ", se a inflação cair.",
            "Caso haja aprovação, " + FORMAL,
            FORMAL[:-1] + " caso as projeções sejam mantidas.",
            "Em cenário hipotético, " + FORMAL,
            CAPTURED_FORMAL.replace("o amplo conjunto de informações disponíveis", "a condição de aprovação futura"),
            CAPTURED_FORMAL.replace("e entende que essa decisão é compatível", "e talvez essa decisão seja compatível"),
        ):
            with self.subTest(value=value):
                self.assertIsNone(copom_record_relation(CLAIM, value, PROOF))

    def test_quoted_rumor_report_negation_and_different_institution_abstain(self):
        for value in (
            '"' + FORMAL + '"', "Segundo um boato, " + FORMAL,
            "Um economista afirmou: " + FORMAL, FORMAL.replace("Copom", "Fed"),
            FORMAL.replace("decidiu", "não decidiu"), FORMAL.replace("decidiu", "poderia decidir"),
            FORMAL.replace("decidiu", "decidirá"), FORMAL.replace("O Copom decidiu", "O Copom anunciou que pretende"),
            FORMAL.replace("decidiu, por unanimidade, elevar", "elevou"),
            "Publicado em 18 de setembro de 2024. " + FORMAL,
        ):
            with self.subTest(value=value):
                self.assertIsNone(copom_record_relation(CLAIM, value, PROOF))

    def test_two_decisions_or_prior_rates_outside_own_frame_never_supply_transition(self):
        for value in (
            "Antes a Selic era 10,50%. O Copom decidiu elevar a Selic para 10,75% ao ano.",
            FORMAL + " O Copom decidiu reduzir a Selic para 10,50% ao ano.",
            FORMAL[:-1] + " e reduzir a inflação para 3,00% ao ano.",
            "Tabela: anterior 10,50%; atual 10,75%. " + FORMAL,
            FORMAL.replace("em 0,25 ponto percentual,", "em 0,25 ponto percentual e em 0,50 ponto percentual,"),
        ):
            with self.subTest(value=value):
                self.assertIsNone(copom_record_relation(CLAIM, value, PROOF))

    def test_explicit_body_date_must_be_full_and_same_exact_record(self):
        self.assertEqual(copom_record_relation(CLAIM, "Em 18 de setembro de 2024, " + FORMAL.lower(), PROOF), "supports")
        self.assertIsNone(copom_record_relation(CLAIM, "Em 17 de setembro de 2024, " + FORMAL.lower(), PROOF))
        self.assertIsNone(copom_record_relation(CLAIM, "Em 31 de fevereiro de 2024, " + FORMAL.lower(), PROOF))
        self.assertIsNone(copom_record_relation(CLAIM, "Em setembro de 2024, " + FORMAL.lower(), PROOF))

    def test_resource_limits_and_non_strings_fail_closed(self):
        for value in (None, {}, True, [], 1, "", " " * 3000):
            with self.subTest(value_type=type(value).__name__):
                self.assertIsNone(parse_copom_claim(value))
                self.assertIsNone(copom_record_relation(CLAIM, value, PROOF))
        self.assertIsNone(parse_copom_claim(CLAIM.replace("10,75", "123456789")))
        self.assertIsNone(copom_record_relation(CLAIM, FORMAL.replace("0,25", "NaN"), PROOF))

    def test_dot_thousands_groups_cannot_become_decimal_rate_equality(self):
        self.assertIsNone(parse_copom_claim(CLAIM.replace("10,50", "10.500").replace("10,75", "10.750")))
        self.assertIsNone(copom_record_relation(CLAIM, FORMAL.replace("10,75", "10.750"), PROOF))
        self.assertIsNone(copom_record_relation(CLAIM, FORMAL.replace("0,25", "0.250"), PROOF))


if __name__ == "__main__":
    unittest.main()
