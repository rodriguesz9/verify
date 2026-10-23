"""Institution routing contracts, without per-claim answers or network."""
import unittest

from app.services.source_queries import primary_source_filter


class SourceDiscoveryRoutingTests(unittest.TestCase):
    def test_unknown_subject_does_not_inherit_unrelated_institutional_sites(self):
        texts = (
            "O Instituto Delta inaugurou o observatório Serra em 1924.",
            "O navio Estrela chegou à ilha Boreal no ano de 1911.",
            "A pesquisadora Lia Monte recebeu o prêmio Aurora em 1932.",
            "O conselho municipal anunciou o fechamento da ponte em 1987.",
        )
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(primary_source_filter(text), "")

    def test_explicit_institution_keeps_its_own_corpus(self):
        cases = (
            ("A NASA publicou o documento sobre o evento Delta.", "nasa.gov"),
            ("A Organização Mundial da Saúde publicou o documento Delta.", "who.int"),
            ("O IBGE publicou o resultado da pesquisa Delta.", "ibge.gov.br"),
            ("O Banco Central publicou o documento sobre a taxa Delta.", "bcb.gov.br"),
            ("O Copernicus divulgou o relatório sobre o evento Delta.", "copernicus.eu"),
        )
        for text, domain in cases:
            with self.subTest(domain=domain):
                self.assertEqual(primary_source_filter(text), f"(site:{domain})")

    def test_multiple_explicit_institutions_do_not_add_other_hosts(self):
        text = "A NASA e a Organização Mundial da Saúde publicaram o documento Delta."
        self.assertEqual(primary_source_filter(text), "(site:who.int OR site:nasa.gov)")

    def test_similar_unknown_name_does_not_gain_an_institutional_alias(self):
        text = "A Organização Mundial do Comércio publicou o documento Delta."
        self.assertEqual(primary_source_filter(text), "")

    def test_deliberate_legacy_fallback_remains_explicit(self):
        text = "A organização Delta publicou o relatório sobre a ponte."
        self.assertEqual(primary_source_filter(text, "legacy-filter"), "legacy-filter")


if __name__ == "__main__":
    unittest.main()
