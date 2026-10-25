"""Discovery hints cannot consume every read on an already usable family."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_attribution as attribution
from app.services.source_corroboration import usable_source_families


CLAIM = "A pesquisadora Zeta morreu em 12 de agosto de 2021."
BBC = "https://www.bbc.com/news/zeta-existing"
BBC_A = "https://www.bbc.com/news/zeta-a"
BBC_B = "https://www.bbc.co.uk/news/zeta-b"
REUTERS = "https://www.reuters.com/world/zeta"
CNN = "https://www.cnnbrasil.com.br/mundo/zeta"


def body(url, text=CLAIM):
    return {"url": url, "title": "Controle sintético", "sentences": [text],
            "sentence_roles": ["body"], "truncated": False, "reference_leads": [],
            "retrieved_at": "2026-10-18T12:00:00+00:00"}


def lead(url, *, cited=False, title=CLAIM):
    result = {"link": url, "title": title}
    if cited:
        result["retrieval_method"] = "ai_selected_candidate_reference"
    return result


def prior_cache(*, usable=True):
    return {BBC: body(BBC) if usable else {"failure": "timeout"},
            **{f"https://www.bbc.com/old-{index}": {"failure": "blocked_or_unavailable"}
               for index in range(7)}}


class RetrievalFamilyOpportunityTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, leads, *, cache=None, maximum=10, submitted=None):
        cache = prior_cache() if cache is None else cache
        with patch.object(attribution, "_fetch_article", new=AsyncMock(side_effect=body)) as fetch:
            result = await attribution.collect_source_attribution(
                CLAIM, [CLAIM], source_url=submitted,
                search_results=[*leads, *[lead(url, title="") for url in cache]],
                include_documents=True, fetched_cache=cache, max_sources=maximum)
        return result, [call.args[0] for call in fetch.await_args_list], cache

    async def test_uncited_independent_family_precedes_two_cited_already_usable_pages(self):
        cache = prior_cache()
        self.assertEqual(usable_source_families(CLAIM, list(cache.values())), {"bbc"})
        result, calls, cache = await self.collect(
            [lead(BBC_A, cited=True), lead(BBC_B, cited=True), lead(REUTERS)], cache=cache)
        self.assertEqual(calls, [REUTERS, BBC_A])
        self.assertEqual(len(cache), 10)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 10)
        self.assertNotIn("veracity_status", result)  # queue order is not a vote

    async def test_each_new_family_gets_one_slot_before_same_family_alias(self):
        result, calls, _ = await self.collect(
            [lead(BBC_A, cited=True), lead(BBC_B, cited=True), lead(REUTERS)],
            cache={}, maximum=2)
        self.assertEqual(calls, [BBC_A, REUTERS])
        self.assertEqual(result["coverage"]["new_fetch_count"], 2)

    async def test_irrelevant_independent_page_does_not_jump_a_relevant_cited_body(self):
        _, calls, _ = await self.collect(
            [lead(BBC_A, cited=True), lead(REUTERS, title="Relatório de agricultura regional")],
            maximum=9)
        self.assertEqual(calls, [BBC_A])

    async def test_cited_unrelated_page_does_not_jump_relevant_uncited_body(self):
        _, calls, _ = await self.collect(
            [lead(BBC_A, cited=True, title="Relatório de agricultura regional"), lead(REUTERS)],
            maximum=9)
        self.assertEqual(calls, [REUTERS])

    async def test_cited_explicit_wrong_period_does_not_jump_matching_period(self):
        _, calls, _ = await self.collect(
            [lead(BBC_A, cited=True, title="Zeta morreu em agosto de 2022"), lead(REUTERS)],
            maximum=9)
        self.assertEqual(calls, [REUTERS])

    async def test_failed_cached_family_allows_another_body_without_refunding_attempts(self):
        cache = prior_cache(usable=False)
        self.assertEqual(usable_source_families(CLAIM, list(cache.values())), set())
        result, calls, cache = await self.collect(
            [lead(BBC_A, cited=True), lead(REUTERS)], cache=cache)
        self.assertEqual(calls, [BBC_A, REUTERS])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 10)
        self.assertEqual(result["coverage"]["fetch_failure_counts"]["timeout"], 1)
        self.assertNotIn(BBC, calls)

    async def test_cached_wire_dependency_uses_actual_family_not_host(self):
        cache = {CNN: body(CNN, "Por Reuters. " + CLAIM),
                 **{f"https://www.cnnbrasil.com.br/old-{index}": {"failure": "timeout"}
                    for index in range(7)}}
        self.assertEqual(usable_source_families(CLAIM, list(cache.values())), {"reuters"})
        _, calls, _ = await self.collect(
            [lead(REUTERS, cited=True), lead(BBC_A)], cache=cache, maximum=9)
        self.assertEqual(calls, [BBC_A])

    async def test_duplicate_urls_and_host_aliases_do_not_gain_extra_family_opportunities(self):
        _, calls, _ = await self.collect(
            [lead(BBC_A, cited=True), lead(BBC_A), lead(BBC_B, cited=True),
             lead(REUTERS), lead(CNN)], cache={}, maximum=3)
        self.assertEqual(calls, [BBC_A, REUTERS, CNN])
        self.assertEqual(len(calls), len(set(calls)))

    async def test_submitted_page_stays_first_and_its_family_is_not_independent(self):
        _, calls, _ = await self.collect(
            [lead(BBC_A, cited=True), lead(REUTERS)], cache={}, maximum=2, submitted=BBC)
        self.assertEqual(calls, [BBC, REUTERS])

    async def test_exhausted_cache_never_retries_or_refunds_a_failed_attempt(self):
        cache = {f"https://www.bbc.com/old-{index}": {"failure": "timeout"} for index in range(10)}
        result, calls, _ = await self.collect([lead(REUTERS)], cache=cache)
        self.assertEqual(calls, [])
        self.assertEqual(result["coverage"]["new_fetch_count"], 0)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 10)
