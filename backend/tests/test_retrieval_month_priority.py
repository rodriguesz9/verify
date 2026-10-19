"""Offline discovery order only; date hints do not supply factual evidence."""
from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_attribution import (
    _lead_month_periods, _retrieval_priority, collect_source_attribution,
)


CLAIM = "Em setembro de 2021, o Conselho Alfa elevou a taxa para 3,5% ao ano."
BASE = "https://www.ibge.gov.br/"


class RetrievalMonthPriorityTests(unittest.IsolatedAsyncioTestCase):
    def rank(self, title, path, claim=CLAIM):
        return _retrieval_priority(claim, title, BASE + path)

    def test_requested_numeric_path_period_precedes_unknown_and_other_month(self):
        exact = self.rank("Conselho Alfa decide taxa", "2021-09/conselho-taxa/")
        unknown = self.rank("Conselho Alfa decide taxa em 2021", "conselho-taxa/")
        other = self.rank("Conselho Alfa decide taxa", "2021-12/conselho-taxa/")
        self.assertLess(exact, unknown)
        self.assertLess(unknown, other)

    def test_portuguese_and_english_named_dates_are_discovery_aliases(self):
        for title in ("Conselho Alfa: 18 de setembro de 2021", "Conselho Alfa: September 18, 2021",
                      "Conselho Alfa: setembro de 2021", "Conselho Alfa: Sept. 2021"):
            with self.subTest(title=title):
                self.assertEqual(self.rank(title, "taxa/")[0], 0)
        self.assertEqual(_lead_month_periods("", "/conselho-setembro-2021/"), {("2021", 9)})

    def test_numeric_directory_path_and_other_year_remain_distinct(self):
        self.assertEqual(self.rank("Conselho Alfa", "2021/09/taxa/")[0], 0)
        self.assertEqual(self.rank("Conselho Alfa", "2022/09/taxa/")[0], 2)

    def test_publication_prefix_does_not_override_reported_event_period(self):
        claim = "Na divulgação de 7 de março de 2022, o Conselho Alfa informou que elevou a taxa em setembro de 2021."
        self.assertEqual(self.rank("Conselho Alfa", "2021-09/taxa/", claim)[0], 0)
        self.assertEqual(self.rank("Conselho Alfa", "2022-03/taxa/", claim)[0], 2)

    def test_ambiguous_claim_dates_do_not_guess_an_event_month_or_year(self):
        claims = ("O Conselho Alfa comparou a taxa de setembro e dezembro de 2021.",
                  "O Conselho Alfa comparou a taxa de setembro de 2021 com a de 2020.")
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertEqual(self.rank("Conselho Alfa", "2021-09/taxa/", claim)[0], 0)
                self.assertEqual(self.rank("Conselho Alfa", "2021-12/taxa/", claim)[0], 0)

    def test_no_requested_month_preserves_year_and_narrower_period_priority(self):
        claim = "Em 2021, o Instituto Alfa publicou o crescimento do produto."
        annual = self.rank("Produto em 2021", "annual-2021/", claim)
        quarter = self.rank("Produto no trimestre de 2021", "quarter-2021/", claim)
        later = self.rank("Produto em 2022", "annual-2022/", claim)
        self.assertLess(annual, quarter)
        self.assertLess(annual, later)

    def test_modal_may_is_not_a_requested_calendar_month(self):
        claim = "The Alpha mission may launch in 2021."
        self.assertEqual(self.rank("Alpha mission", "2021-05/mission/", claim)[0], 0)
        self.assertEqual(self.rank("Alpha mission", "2021-09/mission/", claim)[0], 0)

    def test_query_fragment_invalid_month_and_separate_fields_do_not_make_period(self):
        self.assertEqual(self.rank("Conselho Alfa em 2021", "taxa/?date=2021-09#2021-09")[0], 1)
        self.assertEqual(self.rank("Conselho Alfa em 2021", "2021-13/taxa/")[0], 1)
        self.assertEqual(_lead_month_periods("Conselho em setembro", "/2021/taxa/"), set())

    async def test_unknown_and_other_month_candidates_are_not_filtered_or_truth_evidence(self):
        leads = [
            {"link": BASE + "2021-12/taxa/", "title": "Conselho Alfa decide taxa"},
            {"link": BASE + "taxa-2021/", "title": "Conselho Alfa decide taxa em 2021"},
            {"link": BASE + "2021-09/taxa/", "title": "Conselho Alfa decide taxa"},
        ]
        async def fetch(url):
            return {"url": url, "title": "Outro assunto", "sentences": ["Outro assunto sem prova da afirmação."],
                    "sentence_roles": ["body"], "truncated": False,
                    "retrieved_at": datetime.now(timezone.utc).isoformat()}

        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=leads,
                include_documents=True, max_sources=3)
        self.assertEqual([call.args[0] for call in request.await_args_list],
                         [leads[2]["link"], leads[1]["link"], leads[0]["link"]])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 3)
        self.assertEqual(result["matches"], [])


if __name__ == "__main__":
    unittest.main()
