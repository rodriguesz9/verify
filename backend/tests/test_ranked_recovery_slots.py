"""Offline retrieval-order controls; ranking supplies no factual evidence."""
from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_attribution import collect_source_attribution


CLAIM = "Em 2021, o Instituto Alfa informou que o produto cresceu em relação ao ano anterior."
OTHER = "Outro assunto aparece nesta página sem comprovar a alegação de entrada."


def lead(path, title, host="www.ibge.gov.br", **extra):
    return {"link": f"https://{host}/{path}/", "title": title, **extra}


def document(url, text=OTHER):
    return {"url": url, "title": "Documento de controle", "sentences": [text],
            "sentence_roles": ["body"], "truncated": False,
            "retrieved_at": datetime.now(timezone.utc).isoformat()}


class RankedRecoverySlotsTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, leads, *, limit=3, cache=None, source_url=None):
        async def fetch(url):
            return document(url, CLAIM if url == source_url else OTHER)

        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], source_url,
                search_results=leads, include_documents=True, max_sources=limit,
                fetched_cache=cache)
        return result, [call.args[0] for call in request.await_args_list]

    async def test_remaining_same_family_slots_keep_reference_year_priority(self):
        later_a = lead("annual-2022", "Produto em 2022")
        later_b = lead("annual-2023", "Produto em 2023")
        annual_a = lead("annual-2021-a", "Produto em 2021")
        annual_b = lead("annual-2021-b", "Produto em 2021")
        result, called = await self.collect([later_a, later_b, annual_a, annual_b])
        self.assertEqual(called, [annual_a["link"], annual_b["link"], later_a["link"]])
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 3)

    async def test_same_family_annual_pages_do_not_lose_slots_to_unsought_quarter(self):
        quarter = lead("produto-trimestre-2021", "Produto no primeiro trimestre de 2021")
        annual_a = lead("annual-2021-a", "Produto em 2021")
        annual_b = lead("annual-2021-b", "Produto em 2021")
        result, called = await self.collect([quarter, annual_a, annual_b], limit=2)
        self.assertEqual(called, [annual_a["link"], annual_b["link"]])
        self.assertEqual(result["matches"], [])

    async def test_publisher_diversity_still_precedes_second_page_of_same_family(self):
        later = lead("annual-2022", "Produto em 2022")
        annual_a = lead("annual-2021-a", "Produto em 2021")
        annual_b = lead("annual-2021-b", "Produto em 2021")
        editorial = lead("annual-2021", "Produto em 2021", host="www.bbc.com")
        result, called = await self.collect([later, annual_a, annual_b, editorial])
        self.assertEqual(called, [annual_a["link"], editorial["link"], annual_b["link"]])
        self.assertEqual(result["matches"], [])

    async def test_failed_cache_is_not_retried_and_does_not_reserve_family(self):
        old = lead("old-2021", "Produto em 2021")
        cache = {old["link"]: {"failure": "timeout"},
                 "https://www.bbc.com/failed-one/": {"failure": "blocked_or_unavailable"},
                 "https://www.cnnbrasil.com.br/failed-two/": {"failure": "error"}}
        wrong = lead("annual-2023", "Produto em 2023")
        correct = lead("annual-2021", "Produto em 2021")
        result, called = await self.collect([wrong, old, correct], cache=cache, limit=4)
        self.assertEqual(called, [correct["link"]])
        self.assertEqual(len(cache), 4)
        self.assertEqual(cache[old["link"]], {"failure": "timeout"})
        self.assertEqual(result["coverage"]["new_fetch_count"], 1)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 4)
        self.assertEqual(result["matches"], [])

    async def test_disappeared_failed_urls_still_spend_cumulative_ceiling(self):
        old = lead("old-2021", "Produto em 2021")
        cache = {old["link"]: {"failure": "timeout"},
                 **{f"https://www.bbc.com/failed-{index}/": {"failure": "timeout"}
                    for index in range(5)}}
        correct = lead("annual-2021", "Produto em 2021")
        result, called = await self.collect([correct, old], cache=cache, limit=6)
        self.assertEqual(called, [])
        self.assertEqual(len(cache), 6)
        self.assertEqual(result["coverage"]["new_fetch_count"], 0)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 6)
        self.assertEqual(result["matches"], [])

    async def test_submitted_source_stays_first_and_is_not_independent_reference(self):
        submitted = lead("submitted-2023", "Produto em 2023")
        wrong = lead("annual-2022", "Produto em 2022")
        annual_a = lead("annual-2021-a", "Produto em 2021")
        annual_b = lead("annual-2021-b", "Produto em 2021")
        result, called = await self.collect([wrong, annual_a, annual_b], source_url=submitted["link"])
        self.assertEqual(called, [submitted["link"], annual_a["link"], annual_b["link"]])
        self.assertEqual(result["_documents"][0]["source_role"], "submitted_source")
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["source_role"], "submitted_source")
        self.assertEqual(result["matches"][0]["excerpt"], CLAIM)


if __name__ == "__main__":
    unittest.main()
