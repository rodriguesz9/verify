import unittest
from app.services.source_corroboration import _candidate_passage, _passage_guard, _body_temporal_anchor, _annual_comparison_anchor


class ReportingAnchorTests(unittest.TestCase):
    stamp = "2026-01-01T12:00:00+00:00"
    claim = "Na divulgação de 7 de março de 2025, o IBGE informou que o PIB brasileiro cresceu 3,4% em 2024 em relação a 2023."
    quote = "O IBGE informou nesta sexta-feira (7) que o PIB brasileiro cresceu 3,4% em 2024 na comparação com o ano anterior."

    def passage(self, quote=None, date="2025-03-07"):
        value = quote or self.quote
        return _candidate_passage(value, value, {"publication_date": date})

    def test_explicit_reporting_date_and_annual_reference_remain_distinct(self):
        passage = self.passage()
        self.assertEqual(passage["reporting_anchor"]["publication_date"], "2025-03-07")
        self.assertEqual(passage["annual_comparison_anchor"]["reference_year"], 2023)
        self.assertIsNone(_passage_guard(self.claim, passage, "supports", self.stamp))
        self.assertEqual(passage["quote"], self.quote)

    def test_wrong_release_date_year_value_or_actor_never_matches(self):
        for claim in (self.claim.replace("7 de março", "8 de março"), self.claim.replace("2023", "2022"),
                      self.claim.replace("3,4%", "2,3%"), self.claim.replace("IBGE", "Instituto Zeta")):
            with self.subTest(claim=claim):
                self.assertIsNotNone(_passage_guard(claim, self.passage(), "supports", self.stamp))

    def test_publication_alone_and_wrong_weekday_do_not_date_disclosure(self):
        for quote in (self.quote.replace("nesta sexta-feira (7)", ""), self.quote.replace("sexta-feira", "quinta-feira")):
            passage = self.passage(quote)
            self.assertNotIn("reporting_anchor", passage)
            self.assertIsNotNone(_passage_guard(self.claim, passage, "supports", self.stamp))
        self.assertIsNone(_body_temporal_anchor(self.quote, "2025-03-08", reporting=True))

    def test_annual_reference_is_not_inferred_from_publication_or_quarter(self):
        for quote in ("O PIB cresceu na comparação com o ano anterior.",
                      "Em 2024 o PIB do trimestre cresceu na comparação com o ano anterior.",
                      "Em 2024 houve alta e em 2023 queda na comparação com o ano anterior."):
            self.assertIsNone(_annual_comparison_anchor(quote))

    def test_forged_anchor_rejected_and_disclosure_does_not_date_death(self):
        passage = self.passage()
        passage["reporting_anchor"]["publication_date"] = "2025-03-08"
        self.assertIsNotNone(_passage_guard(self.claim, passage, "supports", self.stamp))
        quote = "A entidade anunciou nesta sexta-feira (7) que a pesquisadora Zeta morreu."
        self.assertIsNone(_body_temporal_anchor(quote, "2025-03-07"))

    def test_completed_annual_gdp_growth_preserves_conventional_reference_year(self):
        quote = "A economia brasileira cresceu 3,4% em 2024, a maior expansão desde 2021. O resultado do PIB foi divulgado nesta sexta-feira (7) pelo IBGE."
        passage = self.passage(quote)
        self.assertEqual(passage["annual_comparison_anchor"]["kind"], "annual_gdp_growth_convention")
        self.assertIsNone(_passage_guard(self.claim, passage, "supports", self.stamp))
        self.assertIsNotNone(_passage_guard(self.claim.replace("2023", "2022"), passage, "supports", self.stamp))
        self.assertIsNone(_annual_comparison_anchor(quote.replace("em 2024", "no trimestre de 2024")))
        self.assertIsNone(_annual_comparison_anchor(quote.replace("cresceu", "vai crescer")))
        self.assertIsNone(_annual_comparison_anchor(quote.replace("economia", "quantidade de objetos")))

    def test_plural_reporting_is_explicit_not_borrowed_from_publication(self):
        quote = "Os dados do PIB foram divulgados nesta sexta-feira (7) pelo IBGE."
        self.assertIsNotNone(_body_temporal_anchor(quote, "2025-03-07", reporting=True))
        self.assertIsNone(_body_temporal_anchor(quote, "2025-03-08", reporting=True))

    def test_annual_inference_does_not_add_unclaimed_period_or_borrow_other_value(self):
        claim = "O PIB brasileiro cresceu 3,4% em 2024."
        quote = "O PIB brasileiro cresceu 3,4% em 2024. O consumo cresceu 5% nesse período."
        passage = self.passage(quote)
        self.assertIsNone(_passage_guard(claim, passage, "supports", self.stamp))
        self.assertIsNotNone(_passage_guard(claim.replace("3,4%", "5%"), passage, "supports", self.stamp))
