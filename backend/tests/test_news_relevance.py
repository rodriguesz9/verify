import unittest
from unittest.mock import AsyncMock, patch

from helpers import app  # isolated credentials before importing pipeline
from app.core.pipeline import run_pipeline
from app.core.serper_client import NewsSearch
from app.models.schemas import FactCheckResult
from app.services.news_relevance import filter_context_news


def news(title, snippet="", **extra):
    return {"title": title, "snippet": snippet, "link": "https://example.org/noticia", **extra}


class NewsRelevanceTests(unittest.TestCase):
    def test_pix_control_excludes_betting_debt_and_generic_matches(self):
        text = "Não pague taxa para liberar seu Pix. Confirme pelo canal oficial."
        items = [news("Cassinos aceitam Pix e oferecem bônus"),
                 news("Pague suas dívidas: veja o canal oficial"),
                 news("Não existe taxa para liberar Pix", "Confira o banco.")]
        kept, audit = filter_context_news(text, items)
        self.assertEqual(kept, [items[2]])
        self.assertEqual(audit["excluded_count"], 2)

    def test_negation_is_not_inverted_and_accents_case_fold(self):
        text = "VACINA não causa AUTISMO."
        items = [news("Vacina causa autismo"), news("Vacina não causa autismo")]
        kept, audit = filter_context_news(text, items)
        self.assertEqual(kept, [items[1]])
        self.assertEqual(audit["excluded_reasons"]["negation_mismatch"], 1)

    def test_explicit_portuguese_values_dates_not_changed(self):
        text = "Benefício de R$ 1.500,00 termina em 14/10/2026."
        items = [news("Benefício termina em 14/10/2026: R$ 1.500,00"),
                 news("Benefício termina em 15/10/2026: R$ 1.500,00"),
                 news("Benefício termina: R$ 150,00 em 14/10/2026"),
                 news("Benefício termina: veja orientações")]
        kept, audit = filter_context_news(text, items)
        self.assertEqual(kept, [items[0], items[3]])
        self.assertEqual(audit["excluded_reasons"]["numeric_mismatch"], 2)

    def test_two_anchors_must_belong_to_one_literal_sentence(self):
        kept, _ = filter_context_news("Pix está disponível. Vacina foi aprovada.", [news("Pix e vacina")])
        self.assertEqual(kept, [])

    def test_bounded_untrusted_snippets_and_no_source_domain_allowlist(self):
        items = [news("Banco bloqueia Pix", source="Publisher", link="https://unlisted.example/a")] * 17
        kept, audit = filter_context_news("Banco bloqueia Pix.", items)
        self.assertEqual(len(kept), 15)
        self.assertEqual(audit["unprocessed_count"], 2)
        self.assertEqual(items[0]["title"], "Banco bloqueia Pix")
        kept, audit = filter_context_news("Banco bloqueia Pix.", [news(None), None])
        self.assertFalse(kept)
        self.assertEqual(audit["excluded_count"], 2)


class NewsPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_with_news(self, result, reviews=()):
        with (patch("app.core.pipeline.search_news", new=AsyncMock(return_value=result)),
              patch("app.core.pipeline.query_fact_check_api", new=AsyncMock(return_value=list(reviews))),
              patch("app.core.pipeline.detect_ai_text", new=AsyncMock(return_value={"ai_probability": None}))):
            return await run_pipeline("Vacina não causa autismo.", use_ai_extraction=False)

    async def test_unrelated_success_remains_visible_context_with_raw_counts(self):
        review = FactCheckResult(claim_text="Vacina não causa autismo.", rating="true", publisher="Exemplo", url="https://example.org/checagem")
        item = news("Cassinos aceitam Pix")
        result = await self.run_with_news(NewsSearch([item]), [review])
        coverage = result["report"]["provider_coverage"]["serper"]
        self.assertEqual(coverage["status"], "success")
        self.assertEqual(coverage["queries"][0]["status"], "success")
        self.assertEqual(coverage["raw_matches_returned"], 1)
        self.assertEqual(coverage["unique_matches_returned"], 1)
        self.assertEqual(coverage["matches_returned"], 1)
        self.assertEqual(result["fact_checks"], [review])
        self.assertEqual(result["report"]["fact_checks"], [review.model_dump()])
        self.assertEqual(len(result["serper_news"]), 1)
        self.assertEqual(result["serper_news"][0]["publisher_assessment"]["level"], "unclassified")
        self.assertEqual(result["metrics"]["serper_news_count"], 1)
        self.assertEqual(result["metrics"]["earliest_known_date"], None)
        self.assertEqual(result["report"]["veracity_status"], "unverified")

    async def test_provider_failure_does_not_become_successful_empty_search(self):
        for status in ("not_configured", "error", "rate_limited"):
            result = await self.run_with_news(NewsSearch(status=status, reason="Unavailable"))
            coverage = result["report"]["provider_coverage"]["serper"]
            self.assertEqual(coverage["status"], "not_configured" if status == "not_configured" else "error")
            self.assertEqual(coverage["queries"][0]["status"], status)

    async def test_related_context_never_votes_on_truth(self):
        item = news("Vacina não causa autismo", date="2026-10-08")
        result = await self.run_with_news(NewsSearch([item]))
        self.assertEqual({key: value for key, value in result["serper_news"][0].items()
                          if key != "publisher_assessment"}, item)
        self.assertEqual(result["serper_news"][0]["publisher_assessment"]["level"], "unclassified")
        self.assertEqual(result["report"]["provider_coverage"]["serper"]["status"], "success")
        self.assertEqual(result["report"]["veracity_status"], "unverified")


if __name__ == "__main__":
    unittest.main()
