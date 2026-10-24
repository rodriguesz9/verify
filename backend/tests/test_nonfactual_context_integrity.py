"""Nonfactual labels cannot certify real-world events. No network or labels in app."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_corroboration as sources
from app.services.source_attribution import collect_official_copom_record
from test_contact_card_body_root import CONTACT, page, parsed, prose
from test_official_copom_flow import CLAIM as COPOM_CLAIM, BODY, COPOM_INDEX_URL, INDEX, DETAIL, DETAIL_URL


CLAIM = "A missão Artemis I foi lançada em 16 de novembro de 2022."
STAMP = "2026-10-23T12:00:00+00:00"
LABELS = ("Ficção: exemplo inventado", "Ficcao: exemplo inventado", "Texto fictício", "Texto ficticio",
          "Narrativa fictícia", "Exemplo hipotético", "Exemplo hipotetico", "Cenário hipotético",
          "Este é um texto simulado.", "Simulação do evento", "Simulacao do evento", "Exemplo inventado",
          "Fictional example", "Fiction: launch record", "Hypothetical example", "Simulated launch",
          "Simulation of the launch", "Invented story")


def documents(label, *, utility=True, external=False):
    if utility:
        markup = page(prose(first=CLAIM) + CONTACT)
        if external:
            markup = markup.replace('<main>', f'<h1>{label}</h1><main>')
        else:
            markup = markup.replace("Registro institucional", label)
    else:
        markup = f'<html><body><article><h1>{label}</h1><p>{CLAIM}</p></article></body></html>'
    # Distinct, equivalent literal mission IDs avoid a duplicated quote/body
    # pretending to supply an independent comparison opportunity.
    return [parsed(markup, "https://www.bbc.com/example"),
            parsed(markup.replace("Artemis I", "Artemis 1"), "https://www.cnn.com/example")]


class NonfactualContextIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def compare(self, docs, claim=CLAIM):
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true"}), \
             patch.object(sources.gemini_client, "generate_text", new=AsyncMock()) as gemini, \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock()) as router:
            result = await sources.corroborate_sources(claim, docs)
        gemini.assert_not_awaited()
        router.assert_not_awaited()
        return result

    async def test_portuguese_and_english_nonfactual_headings_block_two_family_typed_matrix(self):
        for label in LABELS:
            with self.subTest(label=label):
                docs = documents(label)
                self.assertTrue(all(any(label in sentence for sentence in doc["sentences"]) for doc in docs))
                self.assertEqual(sources.usable_source_families(CLAIM, docs), set())
                result = await self.compare(docs)
                self.assertEqual(result["state"], "insufficient")
                self.assertEqual(result["coverage"]["comparison_method"], "not_requested")

    async def test_existing_article_path_and_external_qualifier_cannot_bypass_same_veto(self):
        for label in ("Texto fictício", "Exemplo hipotético", "Simulated launch"):
            for utility, external in ((False, False), (True, True)):
                with self.subTest(label=label, utility=utility, external=external):
                    result = await self.compare(documents(label, utility=utility, external=external))
                    self.assertEqual(result["state"], "insufficient")

    async def test_unlabeled_complete_event_still_has_two_families_and_literal_comparison(self):
        docs = documents("Registro institucional")
        self.assertEqual(sources.usable_source_families(CLAIM, docs), {"bbc", "cnn"})
        result = await self.compare(docs)
        self.assertEqual(result["state"], "corroborated")
        self.assertEqual(result["coverage"]["comparison_method"], "literal_typed_rules_v1")

    def test_refutation_and_false_prefix_do_not_escape_nonfactual_context(self):
        claim = "O Instituto Zeta recebeu o Prêmio Delta em 2007."
        denied = "É falso que " + claim[0].lower() + claim[1:]
        self.assertIsNone(sources._relation_guard(claim, denied, "Boato desmentido. " + denied, "refutes", STAMP))
        for label in LABELS:
            for quote, relation in ((claim, "supports"), (denied, "refutes"),
                                    (claim.replace("recebeu", "não recebeu"), "refutes")):
                context = label + " " + quote
                with self.subTest(label=label, relation=relation):
                    self.assertIsNotNone(sources._relation_guard(claim, quote, context, relation, STAMP))
                    self.assertIsNotNone(sources._passage_guard(claim,
                        {"quote": quote, "context": context}, relation, STAMP))
        for suffix in ("Este é um texto simulado.", "This is a fictional example.", "Isso é ficção."):
            with self.subTest(suffix=suffix):
                self.assertIsNotNone(sources._relation_guard(claim, denied, denied + " " + suffix, "refutes", STAMP))

    async def test_official_record_shortcut_cannot_bypass_nonfactual_label(self):
        async def fetch(url, **_kwargs):
            return {COPOM_INDEX_URL: INDEX, DETAIL_URL: DETAIL}[url]
        cache = {}
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=fetch)):
            await collect_official_copom_record(COPOM_CLAIM, cache, max_sources=3)
        proof = cache[DETAIL_URL]["official_record"]
        passage = {"quote": BODY, "context": BODY, "official_record": proof}
        self.assertIsNone(sources._passage_guard(COPOM_CLAIM, passage, "refutes", STAMP))
        for label in ("Fictional decision", "Exemplo hipotético", "Texto fictício"):
            with self.subTest(label=label):
                self.assertIsNotNone(sources._passage_guard(COPOM_CLAIM,
                    {**passage, "context": label + " " + BODY}, "refutes", STAMP))

    def test_ordinary_word_substrings_and_actual_invention_are_not_fiction_labels(self):
        claim = "O Instituto Zeta recebeu o Prêmio Delta em 2007."
        for introduction in ("A apresentação utiliza ilustrações simplificadas.",
                             "The team invented a new instrument.",
                             "A equipe apresentou um instrumento inventado recentemente."):
            with self.subTest(introduction=introduction):
                self.assertIsNone(sources._relation_guard(claim, claim, introduction + " " + claim, "supports", STAMP))

    def test_later_unrelated_hypothetical_or_explicit_denial_does_not_disavow_current_fact(self):
        claim = "O Instituto Zeta recebeu o Prêmio Delta em 2007."
        for later in ("Na interpretação de outro evento, um cenário hipotético pode ser útil.",
                      "Este texto discute um exemplo hipotético, sem alterar o registro reproduzido.",
                      "Este texto não é hipotético.", "This text is not hypothetical.",
                      "Another hypothetical scenario is discussed separately."):
            with self.subTest(later=later):
                self.assertIsNone(sources._relation_guard(claim, claim, claim + " " + later, "supports", STAMP))

    def test_later_explicit_fiction_of_this_text_or_event_still_blocks(self):
        claim = "O Instituto Zeta recebeu o Prêmio Delta em 2007."
        for later in ("Este texto é fictício.", "Esse evento foi simulado.", "Esta decisão é hipotética.",
                      "Este é um texto simulado.", "This is a fictional example.", "Isso é ficção.",
                      "This event is hypothetical.", "This text is fiction.", "That record was simulated."):
            with self.subTest(later=later):
                self.assertIsNotNone(sources._relation_guard(claim, claim, claim + " " + later, "supports", STAMP))


if __name__ == "__main__":
    unittest.main()
