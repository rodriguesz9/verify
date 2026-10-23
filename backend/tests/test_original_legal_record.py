"""Strict original-record attribution controls, never a general accuracy benchmark."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch


from app.core.openrouter_service import GeneratedText
from test_source_corroboration import reviewed_response
from app.services.source_corroboration import corroborate_sources, document_selection_audit, _candidate_passage, _passage_guard


class OriginalLegalRecordTests(unittest.IsolatedAsyncioTestCase):
    stamp = "2026-10-16T12:00:00+00:00"
    url = "https://www2.camara.leg.br/legin/fed/lei/2010-2019/lei-8541-15-abril-2010-123456-publicacaooriginal-99887-pl.html"
    claim = "O artigo 7º da Lei nº 8.541, de 15 de abril de 2010, não declarou legalmente extinta a taxa no Município Zeta."
    quote = "Art. 7º É declarada extinta a taxa no Município Zeta."
    header = "Legislação Informatizada - LEI Nº 8.541, DE 15 DE ABRIL DE 2010 - Publicação Original"

    def doc(self, **changes):
        value = {"url": self.url, "title": "Registro consultado", "retrieved_at": self.stamp,
            "sentences": [self.header, "LEI Nº 8.541, DE 15 DE ABRIL DE 2010", self.quote],
            "sentence_roles": ["context", "context", "body"], "truncated": False}
        value.update(changes)
        return value

    async def compare(self, claim=None, document=None, relation="refutes", source_url=None):
        async def answer(prompt, **kwargs):
            data = json.loads(prompt)
            evidence = []
            for source in data["sources"]:
                for item in source["passages"]:
                    if item.get("original_legal_publication"):
                        evidence.append({"source_id": source["source_id"], "excerpt_id": item["excerpt_id"], "relation": relation})
                        break
            return reviewed_response(GeneratedText(json.dumps({"claims": [{"claim_id": "c1", "evidence": evidence}]})), prompt)
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "openrouter"}), \
             patch("app.services.source_corroboration.openrouter_service.generate", new=AsyncMock(side_effect=answer)) as model:
            result = await corroborate_sources(claim or self.claim, [document or self.doc()], source_url)
        return result, model

    async def test_one_actual_original_record_confirms_only_its_literal_article_declaration(self):
        result, model = await self.compare()
        self.assertEqual(result["state"], "refuted")
        self.assertEqual(result["claims"][0]["evidence_basis"], "original_institutional_record")
        self.assertIn("única fonte", result["claims"][0]["explanation"])
        record = result["claims"][0]["evidence"][0]
        self.assertEqual(record["excerpt"], self.quote)
        self.assertEqual(record["original_legal_publication"]["header"], self.header)
        model.assert_not_awaited()
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")
        result, _ = await self.compare(self.claim.replace("não declarou", "declarou"), relation="supports")
        self.assertEqual(result["state"], "corroborated")

    async def test_example_wrong_host_replica_updated_or_invented_original_route_remain_insufficient(self):
        for url in ("https://www2.camara.leg.br/legin/exemplo", self.url.replace("www2.camara.leg.br", "mapa.an.gov.br"),
                    self.url.replace("publicacaooriginal", "normaatualizada"), self.url.replace("/fed/", "/municipal/"),
                    self.url.replace("/lei/", "/comentario/"), self.url + "?original=true",
                    self.url.replace("lei-8541", "lei-8542"), self.url.replace("-15-abril", "-16-abril")):
            with self.subTest(url=url):
                result, model = await self.compare(document=self.doc(url=url))
                self.assertEqual(result["state"], "insufficient")
                model.assert_not_awaited()

    async def test_marker_must_be_literal_retrieved_context_header_not_url_title_or_body_comment(self):
        for document in (self.doc(sentences=["Lei nº 8.541, de 15 de abril de 2010", self.quote], sentence_roles=["context", "body"]),
                         self.doc(sentences=[self.header.replace("Publicação Original", "Texto Atualizado"), "Lei nº 8.541, de 15 de abril de 2010", self.quote]),
                         self.doc(sentence_roles=["body", "context", "body"]),
                         self.doc(sentences=["Um comentário sobre " + self.header, "Lei nº 8.541, de 15 de abril de 2010", self.quote])):
            result, model = await self.compare(document=document)
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()

    async def test_mismatched_header_law_article_date_or_payload_never_gain_single_record_status(self):
        for claim in (self.claim.replace("8.541", "8.542"), self.claim.replace("7º", "8º"),
                      self.claim.replace("15 de abril", "16 de abril"), self.claim.replace("taxa", "escravidão"),
                      self.claim.replace("Zeta", "Beta")):
            result, model = await self.compare(claim=claim)
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()
        changed = self.doc()
        changed["sentences"][0] = self.header.replace("8.541", "8.542")
        result, model = await self.compare(document=changed)
        self.assertEqual(result["state"], "insufficient")
        model.assert_not_awaited()

    async def test_denied_identity_far_before_article_is_not_lost_from_original_proof(self):
        document = self.doc(sentences=["Este não é um texto autêntico.", self.header,
            "Observação de identificação.", "Outro parágrafo introdutório.", "Lei nº 8.541, de 15 de abril de 2010", self.quote],
            sentence_roles=["body", "context", "body", "body", "context", "body"])
        result, model = await self.compare(document=document)
        self.assertEqual(result["state"], "insufficient")
        model.assert_not_awaited()

    async def test_submitted_family_wire_quotation_or_title_only_are_not_original_body_evidence(self):
        for document, source_url in ((self.doc(source_role="submitted_source"), None),
                                     (self.doc(), self.url),
                                     (self.doc(), "https://www2.camara.leg.br/legin/outro"),
                                     (self.doc(sentences=[self.header, "Lei nº 8.541, de 15 de abril de 2010", self.quote, "Segundo a Reuters, esta é uma reprodução."],
                                               sentence_roles=["context", "context", "body", "body"]), None),
                                     (self.doc(sentence_roles=["context", "context", "context"]), None)):
            result, model = await self.compare(document=document, source_url=source_url)
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()

    async def test_current_validity_social_effect_and_nested_negation_do_not_fit_narrow_scope(self):
        for claim in (self.claim.replace("não declarou legalmente", "não continua atualmente"),
                      self.claim.replace("extinta a taxa", "extinta a pobreza"),
                      self.claim.replace("legalmente extinta", "legalmente não extinta"),
                      self.claim.replace("2010, não", "2010, que continua em vigor, não"),
                      self.claim.replace("2010, não", "2010 atualmente revogada, não")):
            result, model = await self.compare(claim=claim)
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()
        passage = _candidate_passage(self.quote, self.quote, self.doc())
        self.assertIsNotNone(_passage_guard(self.claim.replace("legalmente extinta", "legalmente não extinta"), passage, "refutes", self.stamp))
        no_anchor = {"quote": "O artigo 7º da Lei nº 8.541, de 15 de abril de 2010, declarou extinta a taxa no Município Zeta.",
                     "context": "Texto do artigo legal."}
        self.assertIsNotNone(_passage_guard(self.claim.replace("legalmente extinta", "legalmente não extinta"), no_anchor, "refutes", self.stamp))

    async def test_original_record_final_decision_preserves_single_source_scope_without_probability(self):
        from app.services.source_decision import apply_source_decision
        result, _ = await self.compare()
        report = {"verdict": "Suspicious", "veracity_status": "unverified", "limitations": [],
            "claim_assessments": [{"claim": self.claim, "status": "insufficient", "evidence": []}]}
        final = apply_source_decision(self.claim, report, result)
        self.assertEqual(final["veracity_status"], "refuted")
        self.assertTrue(final["original_record_only"])
        self.assertIsNone(final["confidence"])
        self.assertIsNone(final["authenticity_percentage"])
        self.assertIn("não duas fontes independentes", final["summary"])

    async def test_original_header_does_not_prove_nonexistent_article_or_missing_body(self):
        for document in (self.doc(sentences=[self.header, "Lei nº 8.541, de 15 de abril de 2010", "Não há reprodução do artigo nesta página."]),
                         self.doc(sentences=[], sentence_roles=[]), self.doc(retrieved_at="2027-01-01T00:00:00+00:00")):
            result, model = await self.compare(document=document)
            self.assertEqual(result["state"], "insufficient")
            model.assert_not_awaited()
