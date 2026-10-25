"""Existing news URLs may guide bounded reads; snippets never become proof."""
import asyncio
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import pipeline
from app.core.serper_client import NewsSearch
from app.services import source_attribution, source_corroboration
from app.services.claim_policy import text_report
from app.services.source_decision import apply_source_decision


TEXT = "O laboratório Alfa confirmou uma observação no observatório Delta em 2021."
OTHER = "Outro assunto sem relação com a observação indicada aparece nesta página."


def lead(index=1, *, host="www.bbc.com", **extra):
    return {"link": f"https://{host}/public-report-{index}/", "title": TEXT, **extra}


def document(url, body=TEXT):
    return {"url": url, "title": "Corpo público de controle", "sentences": [body],
            "sentence_roles": ["body"], "truncated": False, "reference_leads": [],
            "retrieved_at": datetime.now(timezone.utc).isoformat()}


class ContextNewsLeadContractTests(unittest.TestCase):
    def test_only_canonical_urls_titles_and_fixed_discovery_role_survive(self):
        items = NewsSearch([
            {**lead(), "link": "https://WWW.BBC.COM/public-report-1/#section", "snippet": "PRIVATE-SNIPPET",
             "date": "2099-01-01", "source": "TRUSTED-CLAIM", "verdict": "true", "lead_id": "invented",
             "retrieval_method": "inline_cited_primary_reference"},
            lead(),
            lead(2, title="x" * 350),
            lead(3, title={"not": "text"}),
        ])
        selected = pipeline._context_news_reference_leads([items])
        self.assertEqual(len(selected), 3)
        self.assertEqual(selected[0], {"link": lead()["link"], "title": TEXT,
                                       "retrieval_method": "context_news_reference"})
        self.assertEqual(len(selected[1]["title"]), 300)
        self.assertEqual(selected[2]["title"], "")
        self.assertTrue(all(set(item) == {"link", "title", "retrieval_method"} for item in selected))
        self.assertNotIn("PRIVATE-SNIPPET", str(selected))
        self.assertNotIn("TRUSTED-CLAIM", str(selected))

    def test_plain_lists_failures_and_malformed_or_unsafe_links_are_ignored(self):
        unsafe = [
            "http://www.bbc.com/article", "https://user:secret@www.bbc.com/article",
            "https://127.0.0.1/article", "https://www.bbc.com:444/article",
            "https://www.bbc.com.evil.test/article", "https://unknown.example/article",
            "https://www.bbc.com/a bad path", "javascript:alert(1)", None, True,
        ]
        for url in unsafe:
            with self.subTest(unsafe_url=url):
                self.assertEqual(pipeline._context_news_reference_leads([NewsSearch([
                    {"link": url, "title": TEXT},
                ])]), [])
        self.assertEqual(pipeline._context_news_reference_leads([NewsSearch([
            {"url": lead()["link"], "snippet": TEXT},
        ])]), [])
        for status in ("error", "timeout", "rate_limited", "not_configured", "invalid_response", "pending"):
            with self.subTest(status=status):
                self.assertEqual(pipeline._context_news_reference_leads([NewsSearch([lead()], status=status)]), [])
        for values in ([lead()], [RuntimeError("PRIVATE-DETAIL")], [None], {"not": "batches"}, None):
            with self.subTest(values=type(values).__name__):
                self.assertEqual(pipeline._context_news_reference_leads(values), [])
        self.assertEqual(pipeline._context_news_reference_leads([[lead()]]), [])

    def test_three_batches_and_five_items_each_are_hard_discovery_limits(self):
        batches = [NewsSearch([lead(group * 10 + index) for index in range(7)]) for group in range(4)]
        selected = pipeline._context_news_reference_leads(batches)
        self.assertEqual(len(selected), 15)
        self.assertEqual([item["link"] for item in selected],
                         [lead(group * 10 + index)["link"] for group in range(3) for index in range(5)])
        self.assertEqual(pipeline._context_news_reference_leads([NewsSearch(status="no_results")]), [])


class ContextNewsReadLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {
            "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "1",
        }))
        self.research = self.enterContext(patch.object(pipeline, "research_enabled", return_value=False))
        self.web = self.enterContext(patch.object(pipeline, "search_web", new=AsyncMock(return_value=NewsSearch(status="no_results"))))
        self.news = self.enterContext(patch.object(pipeline, "search_news", new=AsyncMock()))
        self.official = self.enterContext(patch.object(pipeline, "collect_official_copom_record", new=AsyncMock(
            return_value={"status": "not_requested"})))
        self.fetch = self.enterContext(patch.object(source_attribution, "_fetch_article", new=AsyncMock(side_effect=document)))
        self.collect = self.enterContext(patch.object(pipeline, "collect_source_attribution", new=AsyncMock(
            wraps=source_attribution.collect_source_attribution)))
        self.planner = self.enterContext(patch.object(pipeline, "plan_source_research", new=AsyncMock(return_value={
            "queries": [], "leads": [], "coverage": {"status": "success", "planned_query_count": 0}})))

    async def completed(self, result):
        return result

    async def retrieve(self, tasks=(), **kwargs):
        return await pipeline._retrieve_source_attribution(TEXT, [TEXT], None,
            context_news_tasks=tasks, **kwargs)

    async def test_late_existing_news_is_awaited_before_reads_without_a_new_search(self):
        entered, release = asyncio.Event(), asyncio.Event()
        items = NewsSearch([lead(), lead(2, host="www.reuters.com")])

        async def delayed():
            entered.set()
            await release.wait()
            return items

        shared = asyncio.create_task(delayed())
        recovery = asyncio.create_task(self.retrieve((shared,)))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.sleep(.01)
            self.assertFalse(recovery.done())
            self.collect.assert_not_awaited()
            self.official.assert_not_awaited()
            self.fetch.assert_not_awaited()
            self.web.assert_awaited_once_with(TEXT)
            self.news.assert_not_awaited()
            release.set()
            result = await asyncio.wait_for(recovery, 1)
        finally:
            release.set()
            for task in (recovery, shared):
                if not task.done():
                    task.cancel()
            await asyncio.gather(recovery, shared, return_exceptions=True)
        self.assertEqual(self.fetch.await_count, 2)
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(result["coverage"]["max_sources"], 3)
        self.assertEqual(result["coverage"]["context_news_recovery"], {
            "status": "success", "awaited_query_count": 1, "candidate_url_count": 2,
            "decision_role": "retrieval_leads_only"})
        self.assertEqual(result["coverage"]["search_status"], "no_results")
        self.assertTrue(all(doc["source_role"] == "retrieved_reference" for doc in result["_documents"]))
        self.web.assert_awaited_once()
        self.planner.assert_not_awaited()
        self.news.assert_not_awaited()

    async def test_default_without_shared_tasks_keeps_ordinary_retrieval_contract(self):
        self.web.return_value = NewsSearch([lead()])
        result = await self.retrieve()
        self.assertEqual(result["coverage"]["context_news_recovery"], {
            "status": "not_requested", "awaited_query_count": 0, "candidate_url_count": 0,
            "decision_role": "retrieval_leads_only"})
        self.web.assert_awaited_once_with(TEXT)
        self.assertEqual(self.fetch.await_count, 1)
        self.assertEqual(len(result["matches"]), 1)
        self.news.assert_not_awaited()

    async def test_recovery_cancellation_preserves_shared_task_until_parent_joins_it(self):
        entered, cleaned = asyncio.Event(), asyncio.Event()

        async def pending():
            entered.set()
            try:
                await asyncio.Future()
            finally:
                await asyncio.sleep(0)
                cleaned.set()

        shared = asyncio.create_task(pending())
        recovery = asyncio.create_task(self.retrieve((shared,)))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.sleep(.01)
            recovery.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await recovery
            self.assertFalse(shared.done())
            self.assertFalse(cleaned.is_set())
            self.fetch.assert_not_awaited()
            await pipeline._await_pipeline_tasks([shared], 0)
            self.assertTrue(shared.cancelled())
            self.assertTrue(cleaned.is_set())
        finally:
            for task in (recovery, shared):
                if not task.done():
                    task.cancel()
            await asyncio.gather(recovery, shared, return_exceptions=True)

    async def test_failed_or_canceled_context_does_not_discard_another_completed_lead(self):
        for failed in (NewsSearch([lead(99)], status="rate_limited"), RuntimeError("PRIVATE-CONTEXT-ERROR"), "cancel"):
            with self.subTest(failure=type(failed).__name__):
                tasks = [asyncio.create_task(self.completed(NewsSearch([lead()])))]
                if failed == "cancel":
                    task = asyncio.create_task(asyncio.sleep(10))
                    task.cancel()
                    tasks.append(task)
                elif isinstance(failed, Exception):
                    async def raise_failure():
                        raise failed
                    tasks.append(asyncio.create_task(raise_failure()))
                else:
                    tasks.append(asyncio.create_task(self.completed(failed)))
                try:
                    result = await self.retrieve(tuple(tasks))
                finally:
                    await asyncio.gather(*tasks, return_exceptions=True)
                coverage = result["coverage"]["context_news_recovery"]
                self.assertEqual(coverage["status"], "partial")
                self.assertEqual(coverage["awaited_query_count"], 2)
                self.assertEqual(coverage["candidate_url_count"], 1)
                self.assertEqual(len(result["matches"]), 1)
                self.assertNotIn("PRIVATE-CONTEXT-ERROR", str(result))

    async def test_web_quota_failure_remains_visible_and_never_starts_recovery_search(self):
        self.web.return_value = NewsSearch(status="rate_limited", reason="Quota unavailable")
        self.research.return_value = True
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}):
            shared = asyncio.create_task(self.completed(NewsSearch([lead()])))
            try:
                result = await self.retrieve((shared,))
            finally:
                await asyncio.gather(shared, return_exceptions=True)
        self.assertEqual(result["coverage"]["search_status"], "rate_limited")
        self.assertEqual(result["coverage"]["search_queries"], [{"method": "whole_literal_claim", "status": "rate_limited"}])
        self.assertEqual(result["coverage"]["context_news_recovery"]["candidate_url_count"], 1)
        self.web.assert_awaited_once()
        self.planner.assert_not_awaited()
        self.assertEqual(self.fetch.await_count, 1)

    async def test_crosscheck_opt_out_does_not_wait_for_or_reuse_context_news(self):
        entered = asyncio.Event()

        async def pending():
            entered.set()
            await asyncio.Future()

        shared = asyncio.create_task(pending())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            result = await asyncio.wait_for(self.retrieve((shared,), use_source_crosscheck=False), 1)
            self.assertFalse(shared.done())
            self.assertEqual(result["coverage"]["context_news_recovery"]["status"], "not_requested")
            self.fetch.assert_not_awaited()
        finally:
            await pipeline._await_pipeline_tasks([shared], 0)

    async def test_only_first_three_owned_news_tasks_are_awaited(self):
        tasks = [asyncio.create_task(self.completed(NewsSearch([lead(index)]))) for index in range(3)]
        ignored = asyncio.create_task(asyncio.sleep(10))
        try:
            result = await asyncio.wait_for(self.retrieve((*tasks, ignored)), 1)
            self.assertFalse(ignored.done())
            self.assertEqual(result["coverage"]["context_news_recovery"]["awaited_query_count"], 3)
            self.assertEqual(result["coverage"]["context_news_recovery"]["candidate_url_count"], 3)
            self.assertEqual(self.fetch.await_count, 3)
        finally:
            await pipeline._await_pipeline_tasks([*tasks, ignored], 0)

    async def test_reused_leads_keep_the_same_three_six_ten_cumulative_read_limits(self):
        for crosscheck, research, ceiling in ((False, False, 3), (True, False, 6), (True, True, 10)):
            with self.subTest(crosscheck=crosscheck, research=research):
                self.fetch.reset_mock()
                self.web.reset_mock()
                self.collect.reset_mock()
                self.fetch.side_effect = lambda _url: {"failure": "timeout"}
                self.web.return_value = NewsSearch([lead(index, host="www.reuters.com") for index in range(10)])
                self.research.return_value = research
                self.planner.return_value = {"queries": [{
                    "query": "laboratório Alfa observatório Delta publicação integral da observação",
                    "source_group": "editorial"}], "leads": [],
                    "coverage": {"status": "success", "planned_query_count": 1}}
                tasks = [asyncio.create_task(self.completed(NewsSearch([
                    lead(group * 10 + index) for index in range(5)]))) for group in range(3)]
                try:
                    with patch.dict(os.environ, {"SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}):
                        result = await self.retrieve(tuple(tasks), use_source_crosscheck=crosscheck)
                finally:
                    await asyncio.gather(*tasks, return_exceptions=True)
                self.assertEqual(self.fetch.await_count, ceiling)
                fetched_urls = [call.args[0] for call in self.fetch.await_args_list]
                self.assertEqual(len(fetched_urls), len(set(fetched_urls)), "Failed reads cannot be retried or refunded.")
                self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], ceiling)
                self.assertEqual(result["matches"], [])
                self.assertLessEqual(self.web.await_count, 5 if research else 3 if crosscheck else 1)
                self.assertTrue(all(call.kwargs.get("max_sources", 3) <= ceiling for call in self.collect.await_args_list))
                self.news.assert_not_awaited()

    async def test_snippets_titles_and_dates_cannot_replace_missing_body_evidence(self):
        self.fetch.side_effect = lambda url: document(url, OTHER)
        items = NewsSearch([
            lead(host="www.bbc.com", snippet=TEXT, date="2021-01-01", source="BBC"),
            lead(host="www.reuters.com", snippet=TEXT, date="2021-01-01", source="Reuters"),
        ])
        shared = asyncio.create_task(self.completed(items))
        try:
            result = await self.retrieve((shared,))
        finally:
            await asyncio.gather(shared, return_exceptions=True)
        self.assertEqual(self.fetch.await_count, 2)
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["_documents"], [])
        self.assertEqual(result["coverage"]["context_news_recovery"]["candidate_url_count"], 2)
        with patch.object(source_corroboration.gemini_client, "generate_text", new=AsyncMock()) as gemini, \
             patch.object(source_corroboration.openrouter_service, "generate", new=AsyncMock()) as router:
            comparison = await source_corroboration.corroborate_sources(TEXT, result["_documents"])
        report = apply_source_decision(TEXT, text_report(TEXT, []), comparison)
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(comparison["state"], "insufficient")
        gemini.assert_not_awaited()
        router.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
