"""Bounded source discovery from later search bodies; not an accuracy corpus."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
from app.core import pipeline
from app.core.serper_client import NewsSearch
from app.services.source_attribution import collect_source_attribution, primary_reference_leads


TEXT = "A missão Aurora IV foi lançada em 11 de maio de 2001."
BASE = ["https://www.bbc.com/base", "https://www.cnnbrasil.com.br/base", "https://brasilescola.uol.com.br/base"]
SECOND = ["https://www.nasa.gov/overview", "https://www.who.int/overview", "https://agenciabrasil.ebc.com.br/overview"]
TARGETS = ["https://www.nasa.gov/aurora/launch", "https://www.who.int/aurora/launch"]


def lead(url):
    return {"link": url, "title": "Aurora mission launch report"}


def document(url, quote="Texto de contexto sem evidência suficiente.", references=(), final_url=None):
    return {"url": final_url or url, "title": "Functional discovery control", "sentences": [quote],
            "sentence_roles": ["body"], "truncated": False, "reference_leads": list(references),
            "retrieved_at": "2026-10-18T12:00:00+00:00"}


def fixture_pages(*, base_references=False, useful=True):
    pages = {url: document(url) for url in [*BASE, *SECOND]}
    if base_references:
        pages[BASE[0]]["reference_leads"] = [lead(url) for url in TARGETS]
    else:
        pages[SECOND[0]]["reference_leads"] = [lead(TARGETS[0])]
        pages[SECOND[1]]["reference_leads"] = [lead(TARGETS[1])]
    quotes = [TEXT, "The Aurora IV mission was launched on May 11, 2001."]
    pages.update({url: document(url, quote if useful else "Outra descrição ocupa este corpo.")
                  for url, quote in zip(TARGETS, quotes)})
    return pages


class LateReferenceRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, pages=None, *, enabled=True, limit="3", timeout_late=False, slow_late=False):
        pages = fixture_pages() if pages is None else pages
        calls, collect_calls = [], []

        async def fetch(url):
            calls.append(url)
            if slow_late and url in TARGETS:
                await asyncio.Event().wait()
            return pages.get(url, {"failure": "blocked_or_unavailable"})

        async def collect(*args, **kwargs):
            collect_calls.append(kwargs["max_sources"] if "max_sources" in kwargs else 3)
            if timeout_late and len(collect_calls) == 3:
                raise TimeoutError("private-diagnostic-do-not-return")
            return await collect_source_attribution(*args, **kwargs)

        responses = [NewsSearch([lead(url) for url in BASE]),
                     NewsSearch([lead(url) for url in SECOND]), NewsSearch([lead(url) for url in SECOND]),
                     NewsSearch(), NewsSearch()]
        empty_plan = {"queries": [], "leads": [], "coverage": {"status": "success", "planned_query_count": 0}}
        original_timeout = asyncio.timeout
        with (patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": limit}),
              patch("app.core.pipeline.asyncio.timeout", side_effect=lambda seconds: original_timeout(.5 if slow_late else seconds)),
              patch("app.core.pipeline.research_enabled", return_value=enabled),
              patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=responses)) as searches,
              patch("app.core.pipeline.plan_source_research", new=AsyncMock(return_value=empty_plan)) as planner,
              patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(side_effect=collect)),
              patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch))):
            result = await pipeline._retrieve_source_attribution(TEXT, [TEXT], None)
        return result, calls, collect_calls, searches, planner

    async def test_second_wave_references_are_read_without_new_search_or_planner(self):
        result, calls, ceilings, searches, planner = await self.run_case()
        self.assertEqual(calls[-2:], TARGETS)
        self.assertEqual(len(calls), 8)
        self.assertEqual(ceilings, [3, 6, 8])
        self.assertEqual(searches.await_count, 3)
        planner.assert_not_awaited()
        self.assertEqual(result["coverage"]["usable_source_family_count"], 2)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 8)
        self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 105)
        self.assertEqual(result["coverage"]["direct_reference_recovery"]["max_leads"], 2)
        self.assertEqual(result["coverage"]["direct_reference_recovery"]["waves"], [
            {"stage": "late_reference", "selected_lead_count": 2, "status": "completed"}])

    async def test_search_limit_one_can_read_real_citations_without_extra_search(self):
        result, calls, ceilings, searches, planner = await self.run_case(fixture_pages(base_references=True), limit="1")
        self.assertEqual(calls[-2:], TARGETS)
        self.assertEqual(ceilings, [3, 5])
        searches.assert_awaited_once()
        planner.assert_not_awaited()
        self.assertEqual(result["coverage"]["usable_source_family_count"], 2)

    async def test_no_ai_configuration_keeps_six_attempt_ceiling(self):
        result, calls, ceilings, searches, planner = await self.run_case(enabled=False)
        self.assertEqual(len(calls), 6)
        self.assertEqual(ceilings, [3, 6])
        self.assertFalse(set(TARGETS) & set(calls))
        self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 45)
        self.assertEqual(result["coverage"]["cited_primary_reference_lead_count"], 0)
        planner.assert_not_awaited()

    def test_attempted_and_redirect_final_urls_are_excluded_before_two_lead_cap(self):
        alias, fresh = "https://www.nasa.gov/redirected", "https://www.who.int/aurora/new"
        references = [lead(TARGETS[0]), lead(alias), lead(fresh)]
        origin = document(BASE[0], references=references)
        cache = {TARGETS[0]: {"failure": "timeout"}, TARGETS[1]: document(TARGETS[1], final_url=alias)}
        found = pipeline._unread_primary_reference_leads(TEXT, [origin], None, cache, [])
        self.assertEqual([item["link"] for item in found], [fresh])
        self.assertEqual(origin["reference_leads"], references)  # Never mutate source records.

    def test_followed_reference_and_its_redirect_alias_cannot_be_discovery_parents(self):
        alias, nested, fresh = "https://www.nasa.gov/redirected", "https://www.nasa.gov/aurora/nested", "https://www.who.int/aurora/new"
        followed = [lead(TARGETS[0])]
        cache = {TARGETS[0]: document(TARGETS[0], final_url=alias)}
        documents = [document(alias, references=[lead(nested)]), document(BASE[0], references=[lead(fresh)])]
        found = pipeline._unread_primary_reference_leads(TEXT, documents, None, cache, followed)
        self.assertEqual([item["link"] for item in found], [fresh])
        self.assertEqual(pipeline._unread_primary_reference_leads(TEXT, documents, None, cache, [*followed, lead(fresh)]), [])

    async def test_callout_title_does_not_provide_body_evidence_or_skip_research(self):
        result, calls, _, _, planner = await self.run_case(fixture_pages(useful=False))
        self.assertTrue(set(TARGETS) <= set(calls))
        self.assertEqual(result["coverage"]["usable_source_family_count"], 0)
        planner.assert_awaited_once()
        self.assertLessEqual(len(calls), 10)

    async def test_identical_bodies_do_not_become_two_independent_families(self):
        pages = fixture_pages()
        pages[TARGETS[1]]["sentences"] = [TEXT]
        result, _, _, _, planner = await self.run_case(pages)
        self.assertEqual(result["coverage"]["usable_source_family_count"], 1)
        planner.assert_awaited_once()

    async def test_late_wave_timeout_preserves_last_completed_collection_and_marks_incomplete(self):
        result, calls, _, _, planner = await self.run_case(timeout_late=True)
        self.assertEqual(len(calls), 6)
        self.assertEqual(result["coverage"]["recovery_status"], "timeout_or_error")
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 6)
        self.assertEqual(result["coverage"]["direct_reference_recovery"]["waves"][-1]["status"], "incomplete")
        self.assertNotIn("private-diagnostic", str(result))
        planner.assert_not_awaited()

    async def test_real_late_dispatch_cancellation_keeps_its_eight_reservations(self):
        result, calls, _, _, planner = await self.run_case(slow_late=True)
        self.assertEqual(len(calls), 8)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 8)
        self.assertEqual(result["coverage"]["recovery_status"], "timeout_or_error")
        self.assertEqual(result["coverage"]["direct_reference_recovery"]["waves"][-1]["status"], "incomplete")
        self.assertEqual(result["coverage"]["usable_source_family_count"], 0)
        planner.assert_not_awaited()

    def test_submitted_source_and_unsafe_reference_never_become_direct_leads(self):
        refs = [lead("http://127.0.0.1/aurora"), lead("https://www.nasa.gov.evil.test/aurora"),
                lead("https://www.nasa.gov/aurora/?token=opaque"), lead(TARGETS[0])]
        self.assertEqual(primary_reference_leads(TEXT, [document(BASE[0], references=refs)],
                                               TARGETS[0]), [])
        submitted = {**document(BASE[0], references=refs), "source_role": "submitted_source"}
        self.assertEqual(pipeline._unread_primary_reference_leads(TEXT, [submitted], None, {}, []), [])

    async def test_failed_direct_target_stays_debited_and_is_not_retried_by_research(self):
        pages = fixture_pages()
        pages[TARGETS[0]] = {"failure": "timeout"}
        result, calls, _, _, planner = await self.run_case(pages)
        self.assertEqual(calls.count(TARGETS[0]), 1)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], len(calls))
        self.assertLessEqual(len(calls), 10)
        planner.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
