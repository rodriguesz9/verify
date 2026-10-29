"""Closed named-month routes diversify discovery, never factual date evidence."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_attribution import (
    _lead_month_periods, _publication_date, _retrieval_priority, collect_source_attribution,
)
from app.services.source_corroboration import document_selection_audit


CLAIM = "Zeta II morreu em 18 de setembro de 2001."
BASE = "https://www.theguardian.com"
STAMP = datetime.now(timezone.utc).isoformat()


class NamedMonthPathPriorityTests(unittest.IsolatedAsyncioTestCase):
    def test_portuguese_and_english_closed_routes_are_calendar_aliases(self):
        for month in ("setembro", "set", "september", "sep", "sept", "SEPTEMBER"):
            with self.subTest(month=month):
                self.assertEqual(_lead_month_periods("", f"/news/2001/{month}/18/report/"), {("2001", 9)})
        for month in ("março", "marco", "march", "mar"):
            with self.subTest(month=month):
                self.assertEqual(_lead_month_periods("", f"/news/2001/{month}/8/"), {("2001", 3)})
        self.assertEqual(_lead_month_periods("", "/2000/feb/29/report"), {("2000", 2)})

    def test_invalid_dates_or_incomplete_segments_are_not_periods(self):
        for route in ("/2001/feb/29/report", "/2001/april/31/report", "/2001/sep/00/report",
                      "/2001/sep/32/report", "/2001/13/18/report", "/2001/unknown/18/report",
                      "/2001/sep/report", "/2001/sep/18th/report", "/2001/sep/180/report",
                      "/12001/sep/18/report", "/2001/septembers/18/report"):
            with self.subTest(route=route):
                self.assertEqual(_lead_month_periods("", route), set())

    def test_title_prose_query_fragment_or_split_fields_cannot_lend_named_route_date(self):
        for title, path in (("A report at /2001/sep/18/", "/report/"),
                            ("", "/report/?next=/2001/sep/18/"),
                            ("", "/report/#/2001/sep/18/"),
                            ("", "A report at /2001/sep/18/"),
                            ("September", "/2001/news/18/"),
                            ("2001", "/sep/18/report/")):
            with self.subTest(title=title, path=path):
                self.assertEqual(_lead_month_periods(title, path), set())
        self.assertEqual(_lead_month_periods("", "/2001/sep/18/report?next=/2002/oct/19/#/2003/nov/20/"),
                         {("2001", 9)})

    def test_matching_route_precedes_unknown_and_later_retrospective(self):
        title = "Zeta II died: the story"
        exact = _retrieval_priority(CLAIM, title, BASE + "/news/2001/sep/18/zeta-died")
        unknown = _retrieval_priority(CLAIM, title, BASE + "/news/zeta-died-2001")
        retrospective = _retrieval_priority(CLAIM, title, BASE + "/news/2001/dec/30/zeta-died")
        self.assertLess(exact, unknown)
        self.assertLess(unknown, retrospective)

    def test_ambiguous_claim_periods_and_existing_numeric_routes_keep_their_rules(self):
        claim = "Zeta II comparou relatos de setembro e dezembro de 2001."
        for month in ("sep", "dec"):
            self.assertEqual(_retrieval_priority(claim, "Zeta II", BASE + f"/2001/{month}/18/report")[0], 0)
        self.assertEqual(_lead_month_periods("", "/news/2001/09/report"), {("2001", 9)})
        self.assertEqual(_lead_month_periods("", "/news/2001-09-18/report"), {("2001", 9)})

    def test_route_date_is_not_publication_metadata_or_a_body_date(self):
        url = BASE + "/news/2001/sep/18/zeta-died"
        quote = "Zeta II morreu pacificamente em sua casa."
        html = ("<html><head><title>Zeta II</title></head><body><article><p>"
                + quote + "</p></article></body></html>").encode()
        resource = SimpleNamespace(data=html, encoding="utf-8", content_type="text/html", final_url=url)
        self.assertIsNone(_publication_date(resource))
        audit = document_selection_audit(CLAIM, [{"url": url, "title": "Zeta II died",
            "sentences": [quote], "sentence_roles": ["body"],
            "truncated": False, "retrieved_at": STAMP, "publication_date": None}], None)
        self.assertEqual(audit["eligible_family_count"], 0)
        self.assertTrue(any("Negação, data ou valor diverge" in row["reason"]
                            for row in audit["reading_gaps"]["claims"][0]["reasons"]))

    async def test_fetch_order_changes_but_route_and_headline_never_prove_claim(self):
        title = "Zeta II died: the story"
        latest, exact = BASE + "/news/2001/dec/30/zeta-died", BASE + "/news/2001/sep/18/zeta-died"
        async def fetch(url):
            return {"url": url, "title": title, "sentences": ["Outro assunto sem prova do fato alegado."],
                    "sentence_roles": ["body"], "truncated": False, "retrieved_at": STAMP}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)) as call:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {"link": latest, "title": title}, {"link": exact, "title": title}],
                include_documents=True, max_sources=2, fetched_cache={})
        self.assertEqual([entry.args[0] for entry in call.await_args_list], [exact, latest])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["matches"], [])


if __name__ == "__main__":
    unittest.main()
