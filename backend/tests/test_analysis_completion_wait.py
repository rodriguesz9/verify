"""Scaled completion/deadline regressions; no live APIs or accuracy sample."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core import gemini_client, openrouter_service, pipeline
from app.services import source_corroboration as comparisons
import test_pipeline_deadline_integrity as pipeline_controls
import test_source_review_generation_contract as review_controls


OFFLINE_ENV = {
    "GEMINI_API_KEY": "offline-not-a-secret", "GEMINI_MODEL_NAME": "offline-control",
    "GEMINI_FALLBACK_MODELS": "", "GEMINI_LOCAL_ADMISSION_ENABLED": "false",
    "OPENROUTER_API_KEY": "offline-not-a-secret", "OPENROUTER_ENABLED": "true",
    "OPENROUTER_MODEL": "openrouter/free", "OPENROUTER_FALLBACK_MODELS": "",
    "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini",
}


def response_for(provider, value="{}"):
    if provider == "gemini":
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
            "content": {"parts": [{"text": value}]}}]})
    return httpx.Response(200, json={"model": "offline/control:free", "choices": [
        {"finish_reason": "stop", "message": {"content": value}}], "usage": {"cost": 0}})


class AnalysisWaitConfigurationTests(unittest.TestCase):
    def test_stage_limits_share_a_bounded_text_pipeline_profile(self):
        from app.core import analysis_timing as timing

        self.assertEqual(timing.MAX_MODEL_WAIT_SECONDS, 120)
        self.assertEqual(timing.TEXT_PIPELINE_WAIT_SECONDS, 420)
        self.assertEqual(timing.TEXT_PARALLEL_WAIT_SECONDS, 150)
        self.assertEqual(timing.SOURCE_RETRIEVAL_WAIT_SECONDS, 145)
        self.assertEqual(timing.RESEARCH_PLAN_WAIT_SECONDS, 60)
        self.assertEqual(timing.RESEARCH_FOLLOWUP_RESERVE_SECONDS, 30)
        self.assertEqual(timing.COMPARISON_WAIT_SECONDS, 240)
        self.assertEqual(pipeline.PIPELINE_BUDGET_SECONDS, timing.TEXT_PIPELINE_WAIT_SECONDS)
        self.assertEqual(pipeline.INITIAL_QUERY_BUDGET_SECONDS, timing.TEXT_PARALLEL_WAIT_SECONDS)
        self.assertLess(timing.SOURCE_RETRIEVAL_WAIT_SECONDS, timing.TEXT_PARALLEL_WAIT_SECONDS)
        self.assertLessEqual(timing.TEXT_PARALLEL_WAIT_SECONDS + timing.COMPARISON_WAIT_SECONDS,
                             timing.TEXT_PIPELINE_WAIT_SECONDS)


class PipelineCompletionOrderingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(pipeline, "PIPELINE_BUDGET_SECONDS", .4))
        self.enterContext(patch.object(pipeline, "INITIAL_QUERY_BUDGET_SECONDS", .15))
        self.enterContext(patch.object(pipeline, "build_fact_check_queries", return_value=(
            pipeline_controls.QUERIES, {"selected_count": len(pipeline_controls.QUERIES)})))
        self.enterContext(patch.object(pipeline, "extract_claims_with_ai", new=AsyncMock()))
        self.enterContext(patch.object(pipeline, "analyze_with_openrouter", new=AsyncMock()))
        self.enterContext(patch.object(pipeline, "query_fact_check_api", new=AsyncMock(
            return_value=pipeline_controls.FactCheckSearch())))
        self.enterContext(patch.object(pipeline, "search_news", new=AsyncMock(
            return_value=pipeline_controls.NewsSearch())))
        self.enterContext(patch.object(pipeline, "detect_ai_text", new=AsyncMock(
            return_value={"ai_probability": None})))
        self.sources = self.enterContext(patch.object(pipeline, "_retrieve_source_attribution",
            new=AsyncMock(return_value=pipeline_controls.attribution())))
        self.comparison = self.enterContext(patch.object(pipeline, "corroborate_sources",
            new=AsyncMock(return_value=pipeline_controls.insufficient_comparison())))

    async def test_waits_for_page_completion_then_comparison_before_returning(self):
        pages_started, pages_release = asyncio.Event(), asyncio.Event()
        comparison_started, comparison_release = asyncio.Event(), asyncio.Event()

        async def pages(*_args, **_kwargs):
            pages_started.set()
            await pages_release.wait()
            return pipeline_controls.attribution()

        async def compare(_text, documents, *_args, **_kwargs):
            self.assertEqual(documents, pipeline_controls.attribution()["_documents"])
            comparison_started.set()
            await comparison_release.wait()
            return pipeline_controls.insufficient_comparison()

        self.sources.side_effect, self.comparison.side_effect = pages, compare
        task = asyncio.create_task(pipeline.run_pipeline(pipeline_controls.TEXT, use_ai_extraction=False))
        try:
            await asyncio.wait_for(pages_started.wait(), .5)
            # Scaled former short window expires; the enlarged shared window
            # must retain the still-pending page rather than fabricate absence.
            await asyncio.sleep(.03)
            self.assertFalse(task.done())
            self.assertFalse(comparison_started.is_set())
            pages_release.set()
            await asyncio.wait_for(comparison_started.wait(), .5)
            self.assertFalse(task.done(), "A started comparison is not a completed report.")
            comparison_release.set()
            result = await asyncio.wait_for(task, .5)
        finally:
            pages_release.set()
            comparison_release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(result["report"]["provider_coverage"]["analysis_budget"]["incomplete_query_count"], 0)
        self.assertEqual(result["report"]["source_attribution"]["status"], "found")
        self.assertEqual(result["report"]["veracity_status"], "unverified")
        self.sources.assert_awaited_once()
        self.comparison.assert_awaited_once()

    async def test_expired_page_wait_joins_cleanup_before_comparison(self):
        cleanup_started, cleanup_release, cleanup_done = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def pages(*_args, **_kwargs):
            try:
                await asyncio.Future()
            finally:
                cleanup_started.set()
                await cleanup_release.wait()
                cleanup_done.set()

        self.sources.side_effect = pages
        with patch.object(pipeline, "INITIAL_QUERY_BUDGET_SECONDS", .02):
            task = asyncio.create_task(pipeline.run_pipeline(pipeline_controls.TEXT, use_ai_extraction=False))
            try:
                await asyncio.wait_for(cleanup_started.wait(), .5)
                self.assertFalse(task.done())
                self.comparison.assert_not_awaited()
            finally:
                cleanup_release.set()
            result = await asyncio.wait_for(task, .5)
        self.assertTrue(cleanup_done.is_set())
        self.assertEqual(self.comparison.await_args.args[1], [])
        self.assertEqual(result["report"]["source_attribution"]["status"], "timeout")
        self.assertEqual(result["report"]["provider_coverage"]["analysis_budget"]["incomplete_query_count"], 1)
        self.assertEqual(result["report"]["veracity_status"], "unverified")


class ModelTransportCompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, OFFLINE_ENV, clear=True))
        self.gemini_reserve = self.enterContext(patch.object(gemini_client, "_reserve_request", new=AsyncMock()))
        self.router_reserve = self.enterContext(patch.object(openrouter_service, "_reserve_request"))

    def mock_transport(self, respond):
        client_type = httpx.AsyncClient
        options = []

        def factory(**kwargs):
            options.append(kwargs)
            return client_type(transport=httpx.MockTransport(respond), **kwargs)

        return patch("httpx.AsyncClient", side_effect=factory), options

    async def invoke(self, provider, timeout):
        operation = gemini_client.generate_text if provider == "gemini" else openrouter_service.generate
        return await operation("offline synthetic input", timeout_seconds=timeout)

    async def test_both_http_transports_accept_120_seconds_without_new_fallbacks(self):
        for provider in ("gemini", "openrouter"):
            sent = []

            async def respond(request):
                sent.append(request)
                return response_for(provider)

            mock, options = self.mock_transport(respond)
            with self.subTest(provider=provider), mock:
                value = await self.invoke(provider, 120)
            self.assertEqual(value, "{}")
            self.assertEqual(len(sent), 1)
            self.assertFalse(options[0]["trust_env"])
            self.assertFalse(options[0]["follow_redirects"])
            timeout = options[0]["timeout"]
            self.assertEqual(timeout.read if isinstance(timeout, httpx.Timeout) else timeout, 120)
            if provider == "openrouter":
                payload = json.loads(sent[0].content)
                self.assertTrue(all(price == 0 for price in payload["provider"]["max_price"].values()))
                self.assertEqual(payload["model"], "openrouter/free")
        self.gemini_reserve.assert_awaited_once()
        self.router_reserve.assert_called_once()

    async def test_above_120_is_rejected_before_client_or_quota_without_echoing_input(self):
        for provider, error_type in (("gemini", gemini_client.GeminiError),
                                     ("openrouter", openrouter_service.OpenRouterError)):
            with self.subTest(provider=provider), patch("httpx.AsyncClient") as factory:
                with self.assertRaises(error_type) as raised:
                    await self.invoke(provider, 121)
            self.assertEqual(raised.exception.status, "invalid_configuration")
            self.assertNotIn("offline-not-a-secret", str(raised.exception))
            self.assertNotIn("offline synthetic input", str(raised.exception))
            factory.assert_not_called()
        self.gemini_reserve.assert_not_awaited()
        self.router_reserve.assert_not_called()

    async def test_response_after_shorter_old_window_is_preserved_until_completion(self):
        for provider in ("gemini", "openrouter"):
            started, release, cleaned = asyncio.Event(), asyncio.Event(), asyncio.Event()
            sends = []

            async def respond(request):
                sends.append(request)
                started.set()
                try:
                    await release.wait()
                    return response_for(provider, '{"complete":true}')
                finally:
                    cleaned.set()

            mock, _ = self.mock_transport(respond)
            with self.subTest(provider=provider), mock:
                task = asyncio.create_task(self.invoke(provider, .15))
                try:
                    await asyncio.wait_for(started.wait(), .5)
                    await asyncio.sleep(.03)
                    self.assertFalse(task.done())
                    self.assertEqual(len(sends), 1, "Pending response must not launch another request.")
                    release.set()
                    value = await asyncio.wait_for(task, .5)
                finally:
                    release.set()
                    if not task.done():
                        task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            self.assertEqual(value, '{"complete":true}')
            self.assertTrue(cleaned.is_set(), provider)
            self.assertEqual(len(sends), 1)

    async def test_hanging_transport_is_canceled_joined_and_not_repeated(self):
        for provider, error_type in (("gemini", gemini_client.GeminiError),
                                     ("openrouter", openrouter_service.OpenRouterError)):
            cleaned = asyncio.Event()
            sends = []

            async def respond(request):
                sends.append(request)
                try:
                    await asyncio.Future()
                finally:
                    await asyncio.sleep(0)
                    cleaned.set()

            mock, _ = self.mock_transport(respond)
            with self.subTest(provider=provider), mock:
                with self.assertRaises(error_type) as raised:
                    await self.invoke(provider, .02)
            self.assertEqual(raised.exception.status, "timeout")
            self.assertTrue(cleaned.is_set(), provider)
            self.assertEqual(len(sends), 1)

    async def test_last_router_attempt_uses_only_outer_timer_and_finishes_async_cleanup(self):
        original_timeout, original_timeout_at = asyncio.timeout, asyncio.timeout_at
        for fallback in ("", "offline/alternate:free"):
            cleanup_started, cleanup_release, cleanup_done = asyncio.Event(), asyncio.Event(), asyncio.Event()
            sends = []

            async def respond(request):
                sends.append(request)
                if fallback and len(sends) == 1:
                    return httpx.Response(503)
                try:
                    await asyncio.Future()
                finally:
                    cleanup_started.set()
                    await cleanup_release.wait()
                    cleanup_done.set()

            mock, _ = self.mock_transport(respond)
            with self.subTest(fallback=bool(fallback)), \
                 patch.dict(os.environ, {"OPENROUTER_FALLBACK_MODELS": fallback}), mock, \
                 patch.object(openrouter_service.asyncio, "timeout", wraps=original_timeout) as outer, \
                 patch.object(openrouter_service.asyncio, "timeout_at", wraps=original_timeout_at) as slices:
                task = asyncio.create_task(self.invoke("openrouter", .03))
                try:
                    await asyncio.wait_for(cleanup_started.wait(), .5)
                    self.assertFalse(task.done(), "Caller must await canceled transport cleanup.")
                finally:
                    cleanup_release.set()
                with self.assertRaises(openrouter_service.OpenRouterError) as raised:
                    await asyncio.wait_for(task, .5)
            self.assertEqual(raised.exception.status, "timeout")
            self.assertTrue(cleanup_done.is_set())
            self.assertEqual(len(sends), 2 if fallback else 1)
            outer.assert_called_once_with(.03)
            self.assertEqual(slices.call_count, 1 if fallback else 0,
                "Only attempts reserving an alternate receive an inner timer.")

    async def test_last_gemini_attempt_uses_only_outer_timer_and_finishes_async_cleanup(self):
        original_timeout, original_timeout_at = asyncio.timeout, asyncio.timeout_at
        for fallback in ("", "offline-alternate"):
            cleanup_started, cleanup_release, cleanup_done = asyncio.Event(), asyncio.Event(), asyncio.Event()
            sends = []
            self.gemini_reserve.reset_mock()

            async def respond(request):
                sends.append(request)
                if fallback and len(sends) == 1:
                    return httpx.Response(503)
                try:
                    await asyncio.Future()
                finally:
                    cleanup_started.set()
                    await cleanup_release.wait()
                    cleanup_done.set()

            mock, _ = self.mock_transport(respond)
            with self.subTest(fallback=bool(fallback)), \
                 patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": fallback}), mock, \
                 patch.object(gemini_client.asyncio, "timeout", wraps=original_timeout) as outer, \
                 patch.object(gemini_client.asyncio, "timeout_at", wraps=original_timeout_at) as slices:
                task = asyncio.create_task(self.invoke("gemini", .03))
                try:
                    await asyncio.wait_for(cleanup_started.wait(), .5)
                    self.assertFalse(task.done(), "Caller must await canceled transport cleanup.")
                finally:
                    cleanup_release.set()
                with self.assertRaises(gemini_client.GeminiError) as raised:
                    await asyncio.wait_for(task, .5)
            self.assertEqual(raised.exception.status, "timeout")
            self.assertTrue(cleanup_done.is_set())
            self.assertEqual(len(sends), 2 if fallback else 1)
            outer.assert_called_once_with(.03)
            self.assertEqual(slices.call_count, 1 if fallback else 0,
                "Only attempts reserving an alternate receive an inner timer.")
            self.assertEqual([call.args[0] for call in self.gemini_reserve.await_args_list],
                             ["offline-control", fallback] if fallback else ["offline-control"])


class ComparisonCompletionOrderingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, OFFLINE_ENV, clear=True))
        self.enterContext(patch.object(comparisons, "typed_review_matrix", return_value=None))

    async def test_primary_can_complete_at_120_second_budget_before_alternate_is_needed(self):
        budgets = []

        async def gemini(prompt, **kwargs):
            budgets.append(kwargs["timeout_seconds"])
            return json.dumps(review_controls.answer(json.loads(prompt), insufficient=True))

        with patch.object(comparisons, "crosscheck_timeout_seconds", return_value=240), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=gemini)) as primary, \
             patch.object(openrouter_service, "generate", new=AsyncMock()) as alternate:
            result = await comparisons.corroborate_sources(review_controls.CLAIM, review_controls.documents(), timeout_seconds=420)
        self.assertEqual(result["state"], "insufficient")
        self.assertTrue(result["coverage"]["complete_source_review"])
        self.assertEqual(len(budgets), 1)
        self.assertGreater(budgets[0], 119)
        self.assertLessEqual(budgets[0], 120)
        primary.assert_awaited_once()
        alternate.assert_not_awaited()

    async def test_pending_primary_does_not_start_alternate_or_return_early(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def gemini(prompt, **_kwargs):
            started.set()
            await release.wait()
            return json.dumps(review_controls.answer(json.loads(prompt), insufficient=True))

        with patch.object(comparisons, "crosscheck_timeout_seconds", return_value=.3), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=gemini)) as primary, \
             patch.object(openrouter_service, "generate", new=AsyncMock()) as alternate:
            task = asyncio.create_task(comparisons.corroborate_sources(
                review_controls.CLAIM, review_controls.documents(), timeout_seconds=.3))
            try:
                await asyncio.wait_for(started.wait(), .5)
                await asyncio.sleep(.03)
                self.assertFalse(task.done())
                alternate.assert_not_awaited()
                release.set()
                result = await asyncio.wait_for(task, .5)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(result["coverage"]["complete_source_review"])
        self.assertEqual(result["state"], "insufficient")
        primary.assert_awaited_once()
        alternate.assert_not_awaited()

    async def test_alternate_retains_its_120_second_share_after_primary_failure(self):
        budgets, sequence = {}, []

        async def gemini(_prompt, **kwargs):
            sequence.append("gemini_finished")
            budgets["gemini"] = kwargs["timeout_seconds"]
            raise gemini_client.GeminiError("Synthetic unavailable provider", "error", 500)

        async def router(prompt, **kwargs):
            self.assertEqual(sequence, ["gemini_finished"])
            sequence.append("openrouter_finished")
            budgets["openrouter"] = kwargs["timeout_seconds"]
            return json.dumps(review_controls.answer(json.loads(prompt), insufficient=True))

        with patch.object(comparisons, "crosscheck_timeout_seconds", return_value=240), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=gemini)) as primary, \
             patch.object(openrouter_service, "generate", new=AsyncMock(side_effect=router)) as alternate:
            result = await comparisons.corroborate_sources(review_controls.CLAIM, review_controls.documents(), timeout_seconds=420)
        self.assertEqual(sequence, ["gemini_finished", "openrouter_finished"])
        self.assertEqual(result["state"], "insufficient")
        self.assertTrue(result["coverage"]["complete_source_review"])
        for budget in budgets.values():
            self.assertGreater(budget, 119)
            self.assertLessEqual(budget, 120)
        primary.assert_awaited_once()
        alternate.assert_awaited_once()
