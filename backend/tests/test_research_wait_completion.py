"""Scaled research completion/deadline controls, not real APIs or accuracy."""
import asyncio
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_research as research


TEXT = "A nave DART da NASA colidiu intencionalmente com o asteroide Dimorphos em 26 de setembro de 2022."
PLAN = {"queries": [{"query": "NASA DART Dimorphos spacecraft intentional impact date",
                     "source_group": "primary"}], "lead_ids": []}
RAW = json.dumps(PLAN)


class ResearchWaitCompletionTests(unittest.IsolatedAsyncioTestCase):
    def configure(self, *, gemini=True, openrouter=True):
        self.enterContext(patch.dict(os.environ, {
            "SERPERAPI_KEY": "offline-test", "SOURCE_RESEARCH_ENABLED": "true",
            "GEMINI_API_KEY": "offline-test" if gemini else "",
            "OPENROUTER_API_KEY": "offline-test" if openrouter else "",
            "OPENROUTER_ENABLED": "true",
        }, clear=True))

    async def run_plan(self, budget=None):
        return await research.plan_source_research(TEXT, [], [], {}, timeout_seconds=budget)

    async def test_default_sixty_seconds_reaches_only_configured_provider_explicitly(self):
        self.configure(gemini=False)
        with patch.object(research.openrouter_service, "generate", new=AsyncMock(return_value=RAW)) as model, \
             patch.object(research.gemini_client, "generate_text", new=AsyncMock()) as absent:
            result = await self.run_plan()
        absent.assert_not_awaited()
        model.assert_awaited_once()
        self.assertEqual(research.TIMEOUT, 60)
        self.assertEqual(result["coverage"]["wait_budget_seconds"], 60)
        self.assertGreater(model.await_args.kwargs["timeout_seconds"], 59)
        self.assertLessEqual(model.await_args.kwargs["timeout_seconds"], 60)

    async def test_late_answers_beyond_old_scaled_cutoffs_are_actually_awaited(self):
        # Scale 60 seconds to .6: answer arrives after the former planner's
        # 45-second cut (.45), and the old implicit OpenRouter25-second cut.
        for name in ("gemini", "openrouter"):
            with self.subTest(provider=name):
                self.configure(gemini=name == "gemini", openrouter=name == "openrouter")
                entered, release = asyncio.Event(), asyncio.Event()
                async def delayed(*_args, **_kwargs):
                    entered.set()
                    await release.wait()
                    return RAW
                target = research.gemini_client if name == "gemini" else research.openrouter_service
                method = "generate_text" if name == "gemini" else "generate"
                with patch.object(target, method, new=AsyncMock(side_effect=delayed)) as model:
                    task = asyncio.create_task(self.run_plan(.6))
                    try:
                        await asyncio.wait_for(entered.wait(), 1)
                        await asyncio.sleep(.46)
                        self.assertFalse(task.done(), "Do not finalize before the real model response.")
                    finally:
                        release.set()
                    result = await asyncio.wait_for(task, 1)
                self.assertEqual(result["queries"], PLAN["queries"])
                self.assertEqual(result["coverage"]["status"], "success")
                provider = result["coverage"]["provider_coverage"][name]
                self.assertGreater(provider["elapsed_seconds"], .45)
                self.assertEqual(provider["attempt_wait_seconds"], model.await_args.kwargs["timeout_seconds"])

    async def test_same_budget_is_passed_to_outer_wait_and_both_transports(self):
        self.configure()
        outer = []
        original_wait = asyncio.wait_for
        async def observed_wait(operation, timeout):
            outer.append(timeout)
            return await original_wait(operation, timeout)
        with patch.object(research.gemini_client, "generate_text", new=AsyncMock(
                 side_effect=research.gemini_client.GeminiError("private-data", "unavailable", 503))) as first, \
             patch.object(research.openrouter_service, "generate", new=AsyncMock(return_value=RAW)) as second, \
             patch.object(research.asyncio, "wait_for", side_effect=observed_wait):
            result = await self.run_plan(.4)
        self.assertEqual(outer, [first.await_args.kwargs["timeout_seconds"], second.await_args.kwargs["timeout_seconds"]])
        self.assertTrue(0 < outer[0] <= .2)
        self.assertTrue(0 < outer[1] <= .4)
        self.assertEqual(result["queries"], PLAN["queries"])
        self.assertNotIn("private-data", json.dumps(result))

    async def test_context_preparation_consumes_the_same_original_deadline(self):
        self.configure(gemini=False)
        now = [100.0]
        def prepare(*_args):
            now[0] += .25
            return {}
        with patch.object(research.asyncio, "get_running_loop", return_value=SimpleNamespace(time=lambda: now[0])), \
             patch.object(research, "_lead_map", side_effect=prepare), \
             patch.object(research.openrouter_service, "generate", new=AsyncMock(return_value=RAW)) as model:
            result = await self.run_plan(.5)
        self.assertAlmostEqual(model.await_args.kwargs["timeout_seconds"], .25)
        self.assertEqual(result["coverage"]["elapsed_seconds"], .25)
        self.assertEqual(result["coverage"]["wait_budget_seconds"], .5)

    async def test_context_exhaustion_never_starts_a_model(self):
        self.configure()
        now = [100.0]
        def prepare(*_args):
            now[0] += .6
            return {}
        with patch.object(research.asyncio, "get_running_loop", return_value=SimpleNamespace(time=lambda: now[0])), \
             patch.object(research, "_lead_map", side_effect=prepare), \
             patch.object(research.gemini_client, "generate_text", new=AsyncMock()) as first, \
             patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
            result = await self.run_plan(.5)
        first.assert_not_awaited()
        second.assert_not_awaited()
        self.assertEqual(result["coverage"]["status"], "timeout")
        self.assertEqual(result["coverage"]["provider_coverage"], {})

    async def test_schema_setup_also_uses_original_deadline_before_any_model(self):
        self.configure()
        now = [100.0]
        def prepare_schema(*_args):
            now[0] += .6
            return {}
        with patch.object(research.asyncio, "get_running_loop", return_value=SimpleNamespace(time=lambda: now[0])), \
             patch.object(research, "_gemini_schema", side_effect=prepare_schema), \
             patch.object(research.gemini_client, "generate_text", new=AsyncMock()) as first, \
             patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
            result = await self.run_plan(.5)
        first.assert_not_awaited()
        second.assert_not_awaited()
        self.assertEqual(result["coverage"]["status"], "timeout")

    async def test_fallback_gets_only_unspent_time_not_a_new_sixty_seconds(self):
        self.configure()
        now = [100.0]
        async def failed(*_args, **_kwargs):
            now[0] += .2
            raise research.gemini_client.GeminiError("private", "unavailable", 503)
        with patch.object(research.asyncio, "get_running_loop", return_value=SimpleNamespace(time=lambda: now[0])), \
             patch.object(research.gemini_client, "generate_text", new=AsyncMock(side_effect=failed)) as first, \
             patch.object(research.openrouter_service, "generate", new=AsyncMock(return_value=RAW)) as second:
            result = await self.run_plan(.6)
        self.assertAlmostEqual(first.await_args.kwargs["timeout_seconds"], .3)
        self.assertAlmostEqual(second.await_args.kwargs["timeout_seconds"], .4)
        self.assertEqual(result["coverage"]["elapsed_seconds"], .2)
        self.assertEqual(result["coverage"]["provider_coverage"]["gemini"]["http_status"], 503)

    async def test_timeout_waits_for_cleanup_before_fallback_and_preserves_remaining_time(self):
        self.configure()
        entered, cleaned = asyncio.Event(), asyncio.Event()
        async def pending(*_args, **_kwargs):
            entered.set()
            try:
                await asyncio.Future()
            finally:
                await asyncio.sleep(0)
                cleaned.set()
        async def alternate(*_args, **_kwargs):
            self.assertTrue(cleaned.is_set())
            return RAW
        with patch.object(research.gemini_client, "generate_text", new=AsyncMock(side_effect=pending)) as first, \
             patch.object(research.openrouter_service, "generate", new=AsyncMock(side_effect=alternate)) as second:
            result = await self.run_plan(.16)
        self.assertTrue(entered.is_set())
        self.assertTrue(cleaned.is_set())
        self.assertEqual(first.await_count, 1)
        self.assertEqual(second.await_count, 1)
        self.assertLess(second.await_args.kwargs["timeout_seconds"], .1)
        self.assertEqual(result["coverage"]["provider_coverage"]["gemini"]["status"], "timeout")

    async def test_cleanup_that_exhausts_total_time_does_not_send_fallback(self):
        self.configure()
        cleanup_entered, release_cleanup = asyncio.Event(), asyncio.Event()
        async def pending(*_args, **_kwargs):
            try:
                await asyncio.Future()
            finally:
                cleanup_entered.set()
                await release_cleanup.wait()
        with patch.object(research.gemini_client, "generate_text", new=AsyncMock(side_effect=pending)), \
             patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
            task = asyncio.create_task(self.run_plan(.12))
            try:
                await asyncio.wait_for(cleanup_entered.wait(), 1)
                await asyncio.sleep(.08)
                self.assertFalse(task.done(), "Wait for canceled provider cleanup.")
                second.assert_not_awaited()
            finally:
                release_cleanup.set()
            result = await asyncio.wait_for(task, 1)
        second.assert_not_awaited()
        self.assertEqual(result["coverage"]["status"], "timeout")
        self.assertNotIn("openrouter", result["coverage"]["provider_coverage"])

    async def test_caller_cancellation_joins_model_cleanup_without_alternate(self):
        self.configure()
        entered, cleanup_entered, release_cleanup, cleaned = (asyncio.Event() for _ in range(4))
        async def pending(*_args, **_kwargs):
            entered.set()
            try:
                await asyncio.Future()
            finally:
                cleanup_entered.set()
                await release_cleanup.wait()
                cleaned.set()
        with patch.object(research.gemini_client, "generate_text", new=AsyncMock(side_effect=pending)), \
             patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
            task = asyncio.create_task(self.run_plan(.6))
            try:
                await asyncio.wait_for(entered.wait(), 1)
                task.cancel()
                await asyncio.wait_for(cleanup_entered.wait(), 1)
                self.assertFalse(task.done())
                second.assert_not_awaited()
            finally:
                release_cleanup.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(cleaned.is_set())
        second.assert_not_awaited()

    async def test_valid_empty_invalid_or_valid_plan_never_requests_another_judgment(self):
        self.configure()
        for raw, expected in ((RAW, "success"), (json.dumps({"queries": [], "lead_ids": []}), "success"),
                              (json.dumps({"queries": [], "lead_ids": ["invented"]}), "invalid_response")):
            with self.subTest(status=expected, raw=raw), \
                 patch.object(research.gemini_client, "generate_text", new=AsyncMock(return_value=raw)) as first, \
                 patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
                result = await self.run_plan(.4)
            first.assert_awaited_once()
            second.assert_not_awaited()
            self.assertEqual(result["coverage"]["status"], expected)

    async def test_invalid_or_exhausted_budget_is_finite_and_never_starts_context_or_io(self):
        self.configure()
        for budget in (True, False, -1, 61, 10 ** 400, float("nan"), float("inf"), float("-inf"), "60", 0):
            with self.subTest(budget=budget), \
                 patch.object(research, "_lead_map") as context, \
                 patch.object(research.gemini_client, "generate_text", new=AsyncMock()) as first, \
                 patch.object(research.openrouter_service, "generate", new=AsyncMock()) as second:
                result = await self.run_plan(budget)
            context.assert_not_called()
            first.assert_not_awaited()
            second.assert_not_awaited()
            self.assertEqual(result["coverage"]["status"], "timeout" if budget == 0 and not isinstance(budget, bool) else "invalid_configuration")
            json.dumps(result, allow_nan=False)
