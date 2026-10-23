"""Counterfeit reproduction scope, using simulated models without network."""
import unittest

import helpers  # disables provider credentials/dotenv before imports
import test_original_legal_record as original_legal_controls


class LegalReproductionScopeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.control = original_legal_controls.OriginalLegalRecordTests()

    def with_footer(self, footer):
        c = self.control
        return c.doc(sentences=[c.header, "Lei nº 8.541, de 15 de abril de 2010", c.quote, footer],
                     sentence_roles=["context", "context", "body", "body"])

    async def test_post_article_fabrication_of_this_reproduction_never_gains_single_record_status(self):
        for footer in ("A reprodução deste artigo é hipotética e não corresponde ao texto original.",
                       "O texto do artigo reproduzido acima foi fabricado para um exercício.",
                       "Este texto é fictício.", "O artigo 7º foi simulado para um exercício.",
                       "Esta reprodução não corresponde ao original.", "Este texto não é original."):
            with self.subTest(footer=footer):
                result, model = await self.control.compare(document=self.with_footer(footer))
                self.assertEqual(result["state"], "insufficient")
                model.assert_not_awaited()

    async def test_standard_editorial_disclaimer_does_not_disavow_the_original_record(self):
        footer = "Este texto não substitui o original publicado no Diário Oficial da União - Seção 1 de 14/05/1888."
        result, model = await self.control.compare(document=self.with_footer(footer))
        self.assertEqual(result["state"], "refuted")
        model.assert_not_awaited()
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")
        self.assertEqual(result["claims"][0]["evidence_basis"], "original_institutional_record")
        positive, _ = await self.control.compare(claim=self.control.claim.replace("não declarou", "declarou"),
            document=self.with_footer(footer), relation="supports")
        self.assertEqual(positive["state"], "corroborated")

    async def test_hypothetical_mention_elsewhere_is_not_a_global_original_record_block(self):
        for footer in ("Na interpretação de outra lei, um cenário hipotético pode ser útil.",
                       "Este texto discute um exemplo hipotético, sem alterar o artigo reproduzido.",
                       "Este texto não é hipotético.",
                       "O texto do artigo 8º foi fabricado para um exercício."):
            with self.subTest(footer=footer):
                result, model = await self.control.compare(document=self.with_footer(footer))
                self.assertEqual(result["state"], "refuted")
                model.assert_not_awaited()
                self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")

    async def test_late_scoped_fabrication_is_not_lost_beyond_the_local_quote_context(self):
        c = self.control
        document = c.doc(sentences=[c.header, "Lei nº 8.541, de 15 de abril de 2010", c.quote,
            "Parágrafo explicativo neutro.", "Outra informação neutra.",
            "Esta reprodução é fictícia."],
            sentence_roles=["context", "context", "body", "body", "body", "body"])
        result, model = await c.compare(document=document)
        self.assertEqual(result["state"], "insufficient")
        model.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
