"""Discovery controls, not a benchmark of truth classification."""
import unittest

from app.services.source_queries import neutral_source_query, primary_source_query, primary_source_filter


class SourceQueryTests(unittest.TestCase):
    def test_local_institutions_keep_native_topic_and_reported_period_not_release_year(self):
        text = "Na divulgação de 12 de agosto de 2021, o IBGE informou que o PIB brasileiro cresceu 4,2% em 2020."
        query = primary_source_query(text)
        for word in ("IBGE", "PIB", "2020"):
            self.assertIn(word, query.split())
        for word in ("GDP", "divulgação", "informou", "12", "4,2", "agosto", "2021"):
            self.assertNotIn(word, query.split())
        monetary = "Em 12 de agosto de 2021, o Copom alterou a taxa Selic."
        self.assertIn("agosto", primary_source_query(monetary).split())
        self.assertIn("2021", primary_source_query(monetary).split())

    def test_recovery_does_not_require_disputed_polarity_day_or_amount(self):
        text = "Em 12 de agosto de 2021, o Instituto Alfa não reduziu a taxa Beta de 7,25% para 6,50%."
        original = text
        query = neutral_source_query(text)
        for word in ("Instituto", "Alfa", "Beta", "taxa", "2021"):
            self.assertIn(word, query.split())
        for word in ("não", "reduziu", "12", "agosto", "7,25", "6,50"):
            self.assertNotIn(word, query.split())
        self.assertEqual(text, original)

    def test_names_and_topic_are_preserved_without_creating_entities(self):
        text = "A agência Zeta classificou o fenômeno Delta como tempestade em 2023."
        query = neutral_source_query(text)
        self.assertIn("Zeta", query)
        self.assertIn("Delta", query)
        self.assertTrue(all(word in text for word in query.split()))

    def test_empty_unknown_or_oversize_input_is_not_rewritten(self):
        for text in (None, "", "12/10/2026", "não " * 100, "Alfa " * 110):
            self.assertIsNone(neutral_source_query(text))

    def test_primary_lead_bridges_only_explicit_identity_and_topic_vocabulary(self):
        text = "Em 11 de março de 2020, a Organização Mundial da Saúde caracterizou a COVID-19 como uma pandemia."
        query = primary_source_query(text)
        for word in ("WHO", "COVID-19", "pandemic", "2020"):
            self.assertIn(word, query.split())
        for word in ("11", "março", "Organização"):
            self.assertNotIn(word, query.split())
        self.assertNotIn("WHO", primary_source_query("A Organização Mundial do Comércio registrou o evento Zeta em 2021."))

    def test_named_institution_routes_discovery_not_the_answer(self):
        self.assertEqual(primary_source_filter("O resultado da NASA sobre o evento Zeta.", "fallback"), "(site:nasa.gov)")
        self.assertEqual(primary_source_filter("A Organização Mundial da Saúde publicou o documento.", "fallback"), "(site:who.int)")
        self.assertEqual(primary_source_filter("A organização Zeta mudou de opinião.", "fallback"), "fallback")
