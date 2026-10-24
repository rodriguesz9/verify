"""Synthetic cancellation/coverage controls; no network or accuracy sample."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core import pipeline
from app.core import gemini_client
from app.core.fact_checker import FactCheckSearch
from app.core.serper_client import NewsSearch
from app.models.schemas import FactCheckResult


TEXT = "O laboratório Alfa registrou uma observação no observatório Delta."
QUERIES = ["completed-query", "pending-query"]


def attribution():
    return {"status": "found", "matches": [{"url": "https://www.bbc.com/synthetic-control"}],
        "coverage": {"synthetic_completed_read": True}, "_documents": [{"synthetic_document": True}]}


def insufficient_comparison():
    return {"version": "source_corroboration_v1", "status": "not_requested", "state": "insufficient",
        "decision_role": "grounded_source_comparison", "claims": [], "coverage": {}}


class PipelineTaskJoinTests(unittest.IsolatedAsyncioTestCase):
    async def test_zero_budget_cancels_new_tasks_before_they_can_start_io(self):
        started = []

        async def pending():
            started.append(True)
            await asyncio.Future()

        tasks = [asyncio.create_task(pending()) for _ in range(2)]
        await pipeline._await_pipeline_tasks(tasks, 0)
        self.assertEqual(started, [])
        self.assertTrue(all(task.cancelled() for task in tasks))

    async def test_timeout_keeps_completed_values_and_joins_pending_cleanup(self):
        cleanup_entered, cleanup_release, cleanup_done = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def completed():
            return {"completed": True}

        async def failed():
            raise ValueError("synthetic-failure")

        async def pending():
            try:
                await asyncio.Future()
            finally:
                cleanup_entered.set()
                await cleanup_release.wait()
                cleanup_done.set()

        tasks = [asyncio.create_task(operation()) for operation in (completed, failed, pending)]
        waiter = asyncio.create_task(pipeline._await_pipeline_tasks(tasks, .01))
        try:
            await asyncio.wait_for(cleanup_entered.wait(), timeout=1)
            self.assertFalse(waiter.done(), "Parent must wait for canceled I/O cleanup.")
        finally:
            cleanup_release.set()
            await asyncio.wait_for(waiter, timeout=1)
        self.assertEqual(tasks[0].result(), {"completed": True})
        self.assertIsInstance(tasks[1].exception(), ValueError)
        self.assertTrue(tasks[2].cancelled())
        self.assertTrue(cleanup_done.is_set())
        self.assertFalse(pipeline._task_failed(tasks[0]))
        self.assertTrue(pipeline._task_failed(tasks[1]))
        self.assertTrue(pipeline._task_failed(tasks[2]))

    async def test_caller_cancellation_joins_every_child_and_propagates(self):
        started, cleaned = set(), set()
        all_started = asyncio.Event()

        async def pending(label):
            started.add(label)
            if len(started) == 2:
                all_started.set()
            try:
                await asyncio.Future()
            finally:
                await asyncio.sleep(0)
                cleaned.add(label)

        tasks = [asyncio.create_task(pending(label)) for label in ("first", "second")]
        waiter = asyncio.create_task(pipeline._await_pipeline_tasks(tasks, 90))
        await asyncio.wait_for(all_started.wait(), timeout=1)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertEqual(cleaned, started)
        self.assertTrue(all(task.cancelled() for task in tasks))


class GeminiComparisonDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_per_call_90_seconds_overrides_shorter_extraction_default(self):
        original_timeout = asyncio.timeout
        with patch.object(gemini_client, "gemini_timeout_seconds", return_value=10), \
             patch.object(gemini_client, "_generate_text", new=AsyncMock(return_value="complete")) as transport, \
             patch.object(gemini_client.asyncio, "timeout", wraps=original_timeout) as deadline:
            result = await gemini_client.generate_text("synthetic comparison", timeout_seconds=90)
        self.assertEqual(result, "complete")
        self.assertEqual(transport.await_args.kwargs["deadline"], 90)
        deadline.assert_called_once_with(90)

    async def test_invalid_per_call_budget_is_rejected_before_transport(self):
        for value in (True, False, 0, -1, 121, 10 ** 400, float("nan"), float("inf"), "90"):
            with self.subTest(value=value), \
                 patch.object(gemini_client, "_generate_text", new=AsyncMock()) as transport:
                with self.assertRaises(gemini_client.GeminiError) as raised:
                    await gemini_client.generate_text("synthetic comparison", timeout_seconds=value)
            self.assertEqual(raised.exception.status, "invalid_configuration")
            transport.assert_not_awaited()


class PipelineDeadlineCoverageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(pipeline, "PIPELINE_BUDGET_SECONDS", 1))
        self.enterContext(patch.object(pipeline, "INITIAL_QUERY_BUDGET_SECONDS", .02))
        self.enterContext(patch.object(pipeline, "build_fact_check_queries",
            return_value=(QUERIES, {"selected_count": len(QUERIES)})))
        self.extraction = self.enterContext(patch.object(pipeline, "extract_claims_with_ai", new=AsyncMock()))
        self.router_extraction = self.enterContext(patch.object(pipeline, "analyze_with_openrouter", new=AsyncMock()))
        self.facts = self.enterContext(patch.object(pipeline, "query_fact_check_api", new=AsyncMock(return_value=FactCheckSearch())))
        self.news = self.enterContext(patch.object(pipeline, "search_news", new=AsyncMock(return_value=NewsSearch())))
        self.ai = self.enterContext(patch.object(pipeline, "detect_ai_text", new=AsyncMock(return_value={"ai_probability": .37})))
        self.sources = self.enterContext(patch.object(pipeline, "_retrieve_source_attribution", new=AsyncMock(return_value=attribution())))
        self.comparison = self.enterContext(patch.object(pipeline, "corroborate_sources", new=AsyncMock(return_value=insufficient_comparison())))

    async def run_control(self):
        result = await pipeline.run_pipeline(TEXT, use_ai_extraction=False)
        self.extraction.assert_not_awaited()
        self.router_extraction.assert_not_awaited()
        return result

    async def test_completed_results_survive_other_queries_timing_out(self):
        closed = set()
        review = FactCheckResult(claim_text=TEXT, rating="N/D", publisher="Synthetic control",
            url="https://www.bbc.com/synthetic-review")
        completed_news = {"link": "https://www.bbc.com/synthetic-news", "title": TEXT}

        async def pending(label):
            try:
                await asyncio.Future()
            finally:
                closed.add(label)

        async def facts(query):
            if query == QUERIES[0]:
                return FactCheckSearch([review])
            return await pending("fact")

        async def news(query):
            if query == QUERIES[0]:
                return NewsSearch([completed_news])
            return await pending("news")

        self.facts.side_effect, self.news.side_effect = facts, news
        result = await self.run_control()
        report = result["report"]
        self.assertEqual(result["fact_checks"], [review])
        self.assertEqual(result["serper_news"], [completed_news])
        self.assertEqual(result["metrics"]["text_ai_probability"], .37)
        self.assertEqual(closed, {"fact", "news"})
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(report["source_attribution"]["matches"], attribution()["matches"])
        self.assertNotIn("_documents", report["source_attribution"])
        coverage = report["provider_coverage"]
        self.assertEqual(coverage["google_fact_check"]["status"], "success")
        self.assertEqual([record["status"] for record in coverage["google_fact_check"]["queries"]], ["success", "timeout"])
        self.assertEqual([record["status"] for record in coverage["serper"]["queries"]], ["success", "timeout"])
        self.assertEqual(coverage["analysis_budget"]["incomplete_query_count"], 2)
        self.assertTrue(coverage["web_references"]["synthetic_completed_read"])
        self.assertEqual(self.comparison.await_args.args[1], attribution()["_documents"])
        remaining = self.comparison.await_args.kwargs["timeout_seconds"]
        self.assertGreater(remaining, 0)
        self.assertLess(remaining, 1 - .01)

    async def test_pending_sources_and_detection_are_explicit_incomplete_results(self):
        closed = set()

        def pending(label):
            async def run(*_args, **_kwargs):
                try:
                    await asyncio.Future()
                finally:
                    closed.add(label)
            return run

        self.sources.side_effect = pending("sources")
        self.ai.side_effect = pending("ai")
        result = await self.run_control()
        report = result["report"]
        self.assertEqual(closed, {"sources", "ai"})
        self.assertEqual(report["source_attribution"]["status"], "timeout")
        self.assertEqual(report["provider_coverage"]["web_references"]["status"], "timeout")
        self.assertEqual(report["provider_coverage"]["analysis_budget"]["incomplete_query_count"], 2)
        self.assertIsNone(result["metrics"]["text_ai_probability"])
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(self.comparison.await_args.args[1], [])

    async def test_provider_exception_is_joined_without_leaking_message(self):
        self.sources.side_effect = RuntimeError("synthetic-private-provider-detail")
        result = await self.run_control()
        self.assertEqual(result["report"]["source_attribution"]["status"], "error")
        self.assertEqual(result["report"]["provider_coverage"]["analysis_budget"]["incomplete_query_count"], 0)
        self.assertNotIn("synthetic-private-provider-detail", str(result))

    async def test_exhausted_pipeline_budget_sends_no_parallel_provider_requests(self):
        with patch.object(pipeline, "PIPELINE_BUDGET_SECONDS", 0):
            result = await self.run_control()
        for operation in (self.facts, self.news, self.ai, self.sources):
            operation.assert_not_awaited()
        report = result["report"]
        self.assertEqual(report["provider_coverage"]["analysis_budget"]["incomplete_query_count"], 6)
        self.assertEqual(report["source_attribution"]["status"], "timeout")
        self.assertEqual(report["veracity_status"], "unverified")
        self.assertEqual(self.comparison.await_args.kwargs["timeout_seconds"], 0)

    async def test_caller_cancel_during_parallel_queries_cleans_all_six_children(self):
        started, cleaned, children = set(), set(), set()
        all_started = asyncio.Event()

        def pending(kind):
            async def run(*args, **_kwargs):
                label = (kind, args[0] if kind in {"facts", "news"} else "one")
                started.add(label)
                children.add(asyncio.current_task())
                if len(started) == 6:
                    all_started.set()
                try:
                    await asyncio.Future()
                finally:
                    await asyncio.sleep(0)
                    cleaned.add(label)
            return run

        self.facts.side_effect, self.news.side_effect = pending("facts"), pending("news")
        self.ai.side_effect, self.sources.side_effect = pending("ai"), pending("sources")
        task = asyncio.create_task(pipeline.run_pipeline(TEXT, use_ai_extraction=False))
        try:
            await asyncio.wait_for(all_started.wait(), timeout=1)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(cleaned, started)
        self.assertEqual(len(children), 6)
        self.assertTrue(all(child.cancelled() for child in children))
        self.comparison.assert_not_awaited()

    async def test_caller_cancel_during_comparison_propagates_after_cleanup(self):
        started, cleaned = asyncio.Event(), asyncio.Event()

        async def compare(*_args, **_kwargs):
            started.set()
            try:
                await asyncio.Future()
            finally:
                await asyncio.sleep(0)
                cleaned.set()

        self.comparison.side_effect = compare
        task = asyncio.create_task(pipeline.run_pipeline(TEXT, use_ai_extraction=False))
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(cleaned.is_set())
