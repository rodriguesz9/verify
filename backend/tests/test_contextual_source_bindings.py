"""Body/context identity controls. Offline fixtures, not live accuracy claims."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core.openrouter_service import GeneratedText
from test_source_corroboration import reviewed_response
from app.services.source_corroboration import (
    _candidate_passage, _passage_guard, _body_temporal_anchor,
    _legal_article_anchor, corroborate_sources, document_selection_audit,
)


STAMP = "2026-10-16T12:00:00+00:00"


def doc(sentences, url="https://www2.camara.leg.br/legin/exemplo", roles=None):
    value = {"url": url, "title": "Documento consultado", "sentences": sentences,
             "retrieved_at": STAMP, "truncated": False}
    if roles:
        value["sentence_roles"] = roles
    return value


class LegalArticleBindingsTests(unittest.IsolatedAsyncioTestCase):
    # A fixed normative statement, not a claim about actual social conditions.
    claim = "O artigo 1º da Lei nº 3.353, de 13 de maio de 1888, não declarou legalmente extinta a escravidão no Brasil."
    first = "1º É declarada extincta desde a data d'esta Lei, a escravidão no Brazil."
    second = "1º É declarada extinta, desde a data desta Lei, a escravidão no Brasil."

    def docs(self):
        return [doc(["LEI Nº 3.353, DE 13 DE MAIO DE 1888", "Art.", self.first]),
                doc(["A lei n.", "3.353, de 13 de maio de 1888, possui dois artigos.",
                     "O texto do primeiro é: Art.", self.second],
                    "https://mapa.an.gov.br/historia/ato")]

    async def compare(self, claim=None, documents=None, relation="refutes"):
        async def answer(prompt, **kwargs):
            request = json.loads(prompt)
            evidence = []
            for source in request["sources"]:
                passage = next((item for item in source["passages"] if item.get("legal_article_anchor")), None)
                if passage:
                    evidence.append({"source_id": source["source_id"], "excerpt_id": passage["excerpt_id"], "relation": relation})
            return reviewed_response(GeneratedText(json.dumps({"claims": [{"claim_id": "c1", "evidence": evidence}]})), prompt)
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter", "SOURCE_CROSSCHECK_ENABLED": "true"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=answer)) as model:
            result = await corroborate_sources(claim or self.claim, documents if documents is not None else self.docs())
        return result, model

    async def test_explicit_law_article_identity_and_historical_spelling_preserve_original_quote(self):
        result, model = await self.compare()
        self.assertEqual(result["state"], "refuted")
        model.assert_awaited_once()
        records = result["claims"][0]["evidence"]
        self.assertEqual({item["excerpt"] for item in records}, {self.first, self.second})
        self.assertEqual({item["legal_article_anchor"]["law_date"] for item in records}, {"1888-05-13"})
        self.assertEqual(result["claims"][0]["evidence_basis"], "cross_source_comparison")

    async def test_same_declaration_supports_positive_text_claim_but_never_wrong_actor_number_or_article(self):
        result, _ = await self.compare(self.claim.replace("não declarou", "declarou"), relation="supports")
        self.assertEqual(result["state"], "corroborated")
        for claim in (self.claim.replace("3.353", "3.354"), self.claim.replace("13 de maio", "14 de maio"),
                      self.claim.replace("1º", "2º"), self.claim.replace("Brasil", "Portugal"),
                      self.claim.replace("escravidão", "propriedade")):
            with self.subTest(claim=claim):
                result, _ = await self.compare(claim)
                self.assertEqual(result["state"], "insufficient")

    async def test_one_legal_publication_remains_insufficient(self):
        result, model = await self.compare(documents=self.docs()[:1])
        self.assertEqual(result["state"], "insufficient")
        model.assert_not_awaited()

    def test_unrelated_diploma_values_and_title_alone_never_prove_article(self):
        self.assertIsNone(_legal_article_anchor(self.first, {"sentences": [self.first]}))
        self.assertIsNone(_legal_article_anchor(self.first, {"sentences": [
            "LEI Nº 3.353, DE 13 DE MAIO DE 1888", "Lei nº 3.354, de 14 de maio de 1888", self.first]}))
        missing = doc(["O artigo 1º da Lei nº 3.353, de 13 de maio de 1888 declara extinta a escravidão no Brasil."], roles=["context"])
        self.assertEqual(document_selection_audit(self.claim, [missing])["eligible_family_count"], 0)

    def test_reference_must_be_nearby_article_must_be_unique_and_anchor_revalidated(self):
        self.assertIsNone(_legal_article_anchor(self.first, {"sentences": [
            "LEI Nº 3.353, DE 13 DE MAIO DE 1888", *["Outra informação." for _ in range(5)], self.first]}))
        multi = self.first + " Art. 2º Revogam-se disposições em contrário."
        self.assertIsNone(_legal_article_anchor(multi, {"sentences": ["LEI Nº 3.353, DE 13 DE MAIO DE 1888", multi]}))
        passage = _candidate_passage(self.first, self.first, self.docs()[0])
        passage["legal_article_anchor"]["law_number"] = "3354"
        self.assertIsNotNone(_passage_guard(self.claim, passage, "refutes", STAMP))

    async def test_denied_rumoured_or_fabricated_identity_cannot_lend_law_metadata(self):
        reference = "Lei nº 3.353, de 13 de maio de 1888"
        for opening in (f"É falso que este seja o texto da {reference}.",
                        f"Este não é o texto da {reference}.",
                        f"Uma suposta reprodução da {reference} circulou em um boato.",
                        f"Uma reprodução hipotética da {reference} é mostrada a seguir.",
                        f"Este poderia ser o texto da {reference}."):
            with self.subTest(opening=opening):
                sentences = [opening, "Primeiro parágrafo introdutório.", "Mais uma observação.", "Art.", self.first]
                self.assertIsNone(_legal_article_anchor(self.first, {"sentences": sentences}))
                docs = [doc(sentences), doc(sentences[:-1] + [self.second], "https://mapa.an.gov.br/historia/ato")]
                result, model = await self.compare(documents=docs)
                self.assertEqual(result["state"], "insufficient")
                model.assert_not_awaited()

    async def test_binding_is_generic_and_does_not_grant_current_validity_or_social_effects(self):
        claim = "O artigo 7º da Lei nº 8.541, de 15 de abril de 2010, não declarou legalmente extinta a taxa no Município Zeta."
        quote = "Art. 7º É declarada extinta a taxa no Município Zeta."
        document = doc(["Lei nº 8.541, de 15 de abril de 2010", quote])
        passage = _candidate_passage(quote, quote, document)
        self.assertIsNone(_passage_guard(claim, passage, "refutes", STAMP))
        for invalid in (claim.replace("extinta a taxa", "inexistente a pobreza"),
                        claim.replace("não declarou legalmente", "não continua atualmente"),
                        claim.replace("2010", "2027")):
            self.assertIsNotNone(_passage_guard(invalid, passage, "refutes", STAMP))
        future = doc(["Lei nº 8.541, de 15 de abril de 2027", quote])
        self.assertIsNotNone(_passage_guard(claim.replace("2010", "2027"),
            _candidate_passage(quote, quote, future), "refutes", STAMP))


class DecisionDateBindingsTests(unittest.TestCase):
    quote = "O Comitê Zeta reduziu nesta quarta-feira (18) a taxa de 10,75% para 10,50% ao ano."
    claim = "Em 18 de setembro de 2024, o Comitê Zeta reduziu a taxa de 10,75% para 10,50% ao ano."

    def passage(self, quote=None, published="2024-09-18"):
        quote = quote or self.quote
        return _candidate_passage(quote, quote, {"publication_date": published})

    def test_explicit_direct_action_day_can_resolve_publication_year_and_month(self):
        passage = self.passage()
        self.assertEqual(passage["decision_anchor"]["kind"], "explicit_decision_body_date")
        self.assertIsNone(_passage_guard(self.claim, passage, "supports", STAMP))
        self.assertEqual(passage["quote"], self.quote)

    def test_missing_or_different_explicit_action_date_actor_and_values_abstain(self):
        for quote in (self.quote.replace("nesta quarta-feira (18)", ""),
                      self.quote.replace("quarta-feira", "terça-feira"),
                      self.quote.replace("(18)", "(19)"),
                      self.quote.replace("Comitê Zeta", "Comitê Beta"),
                      self.quote.replace("10,50%", "10,25%")):
            with self.subTest(quote=quote):
                self.assertIsNotNone(_passage_guard(self.claim, self.passage(quote), "supports", STAMP))

    def test_other_announcement_and_future_decision_cannot_borrow_publication_date(self):
        for quote in ("O Comitê Zeta reduziu a taxa e anunciou nesta quarta-feira (18) uma nova reunião.",
                      "O Comitê Zeta vai reduzir nesta quarta-feira (18) a taxa de 10,75% para 10,50% ao ano."):
            self.assertIsNone(_body_temporal_anchor(quote, "2024-09-18", decision=True))
            self.assertIsNotNone(_passage_guard(self.claim, self.passage(quote), "supports", STAMP))

    def test_reversal_needs_same_explicit_day_and_preserves_transition(self):
        quote = self.quote.replace("reduziu", "elevou").replace("10,75% para 10,50%", "10,50% para 10,75%")
        self.assertIsNone(_passage_guard(self.claim, self.passage(quote), "refutes", STAMP))
        self.assertIsNotNone(_passage_guard(self.claim.replace("18 de setembro", "19 de setembro"),
            self.passage(quote), "refutes", STAMP))
