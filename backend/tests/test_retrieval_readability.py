"""Queue/discovery controls, not truth classification or historical answers."""
import unittest
from unittest.mock import AsyncMock, patch

from app.core.pipeline import _source_recovery_queries, EDITORIAL_SITE_FILTER
from app.services.source_attribution import _retrieval_priority, collect_source_attribution
from app.services.source_queries import discovery_target_years, neutral_source_query


TEXT = "Na divulgação de 12 de março de 2003, o Instituto Zeta informou que o produto cresceu 4,2% em 2002 em relação a 2001."


class RetrievalReadabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_comparison_baseline_does_not_displace_measured_year(self):
        self.assertEqual(discovery_target_years(TEXT), {"2002"})
        query = neutral_source_query(TEXT)
        self.assertIn("2002", query)
        self.assertNotIn("2001", query)
        self.assertNotIn("2003", query)
        same = _retrieval_priority(TEXT, "Produto cresce em 2002", "https://www.ibge.gov.br/produto-2002/")
        baseline = _retrieval_priority(TEXT, "Produto cresce em 2001", "https://www.ibge.gov.br/produto-2001/")
        self.assertLess(same, baseline)
        self.assertIn("2001", TEXT)  # original assertion is never rewritten

    def test_baseline_is_only_removed_for_one_closed_explicit_pair(self):
        for text, years in (
            ("O produto cresceu em 2002 compared with 2001.", {"2002"}),
            ("The product grew in 2002 compared to 2001.", {"2002"}),
            ("O produto cresceu em 2002 em relação a 2001 e atingiu outra marca em 2000.", {"2000", "2001", "2002"}),
            ("O produto comparou as taxas de 2002 e 2001.", {"2001", "2002"}),
            ("O produto cresceu em 2002 e em 2001 em relação a 2000.", {"2000", "2001", "2002"}),
        ):
            with self.subTest(text=text):
                self.assertEqual(discovery_target_years(text), years)

    def test_supported_article_precedes_obvious_unsupported_material_without_filtering_it(self):
        claim = "A nave Zeta foi lançada em setembro de 2002."
        html = _retrieval_priority(claim, "Nave Zeta lançamento em 2002", "https://www.nasa.gov/zeta-launch-2002/")
        for path in ("/2002/09/zeta-launch.pdf", "/videos/zeta-launch-2002/", "/galerias/zeta-launch-2002/",
                     "/zeta-launch.MP4", "/zeta-launch.jpeg"):
            with self.subTest(path=path):
                unsupported = _retrieval_priority(claim, "Nave Zeta lançamento setembro 2002", "https://www.nasa.gov" + path)
                self.assertLess(html, unsupported)

    def test_relevant_topic_precedes_unrelated_primary_host_when_period_equal(self):
        claim = "O telescópio espacial Zeta Omega foi lançado em 2002."
        article = _retrieval_priority(claim, "Telescópio espacial Zeta Omega lançamento 2002", "https://www.bbc.com/science/zeta-2002/")
        unrelated = _retrieval_priority(claim, "Atlas escolar do espaço 2002", "https://www.ibge.gov.br/atlas-2002/")
        self.assertLess(article, unrelated)

    def test_editorial_discovery_includes_existing_approved_independent_family(self):
        self.assertIn("site:g1.globo.com", EDITORIAL_SITE_FILTER)
        text = "A Rainha Zeta II morreu em 12 de março de 2002."
        plans = _source_recovery_queries(text, 3)
        self.assertEqual(len(plans), 2)
        self.assertIn("site:g1.globo.com", plans[1][0])
        self.assertTrue(all(len(query) <= 500 for query, _ in plans))

    async def test_same_family_read_slot_uses_article_instead_of_pdf_and_still_requires_body(self):
        text = "O telescópio espacial Zeta Omega foi lançado em 2002."
        pdf = "https://science.nasa.gov/2002/zeta-omega.pdf"
        article = "https://science.nasa.gov/zeta-omega/launch/"
        called = []
        async def fetch(url):
            called.append(url)
            return {"url": url, "title": "Outro assunto", "sentences": ["Outro assunto sem prova da alegação."],
                    "sentence_roles": ["body"], "truncated": False}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)):
            result = await collect_source_attribution(text, [text], search_results=[
                {"link": pdf, "title": "Zeta Omega lançamento 2002"},
                {"link": article, "title": "Zeta Omega lançamento"}], include_documents=True, max_sources=1)
        self.assertEqual(called, [article])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)
        self.assertEqual(result["matches"], [])

    async def test_unsupported_only_lead_is_not_removed_or_refunded_after_failure(self):
        pdf = "https://science.nasa.gov/zeta-omega.pdf"
        cache = {}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(return_value={"failure": "unsupported_content"})) as fetch:
            result = await collect_source_attribution(TEXT, [TEXT], search_results=[{"link": pdf}],
                include_documents=True, max_sources=1, fetched_cache=cache)
            await collect_source_attribution(TEXT, [TEXT], search_results=[{"link": pdf}],
                include_documents=True, max_sources=1, fetched_cache=cache)
        fetch.assert_awaited_once()
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)
        self.assertEqual(result["coverage"]["fetch_failure_counts"]["unsupported_content"], 1)
        self.assertEqual(result["matches"], [])


if __name__ == "__main__":
    unittest.main()
