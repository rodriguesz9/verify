"""Offline local admission waiting: deadlines/cancellation never create HTTP."""
import asyncio
import os
import time
import unittest
from unittest.mock import AsyncMock, patch

import helpers
import httpx
from app.core import gemini_client as gemini


def reply():
    return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
        "content": {"parts": [{"text": '{"ok":true}'}]}}]})


class GeminiAdmissionWaitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = 100.0
        self.guard = gemini.GeminiAdmission(clock=lambda: self.now)
        self.enterContext(patch.object(gemini, "_gemini_admission", self.guard))
        self.enterContext(patch.dict(os.environ, {
            "GEMINI_API_KEY": "offline-unit-placeholder", "GEMINI_MODEL_NAME": "primary-test",
            "GEMINI_FALLBACK_MODELS": "fallback-test", "GEMINI_LOCAL_ADMISSION_ENABLED": "true",
            "GEMINI_LOCAL_REQUESTS_PER_MINUTE": "1", "GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "60",
        }))

    async def pending(self, count):
        for _ in range(200):
            if self.guard._pending_count == count:
                return
            await asyncio.sleep(0)
        self.fail(f"Expected {count} pending requests, observed {self.guard._pending_count}.")

    def advance(self, seconds):
        self.now += seconds
        with self.guard._lock:
            for model in self.guard._waiters:
                self.guard._wake_waiters(model)

    async def test_real_window_timer_admits_without_external_wake_or_fake_clock_advance(self):
        guard = gemini.GeminiAdmission()  # Real monotonic clock throughout.
        guard.reserve("timer-model", 1)
        # A genuinely occupied 60-second window with only 20 ms remaining.
        # No injected sleep/wake/advance: wait's internal timer must resume it.
        with guard._lock:
            guard._models["timer-model"][0][0] -= 59.98
            available_at = guard._models["timer-model"][0][0] + 60
        started = time.monotonic()
        await asyncio.wait_for(guard.wait("timer-model", 1), timeout=1)
        stamps = list(guard._models["timer-model"][0])
        self.assertEqual(len(stamps), 1)
        self.assertGreaterEqual(stamps[0], available_at)
        self.assertGreaterEqual(time.monotonic() - started, .005)
        self.assertEqual(guard._pending_count, 0)
        self.assertEqual(guard._waiters, {})

    async def test_existing_generation_deadline_includes_wait_without_transport_or_fallback(self):
        self.guard.reserve("primary-test", 1)
        with patch.object(gemini, "gemini_timeout_seconds", return_value=.01), \
                patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=reply())) as post:
            with self.assertRaises(gemini.GeminiError) as failure:
                await gemini.generate_text("private-input-never-in-queue")
        self.assertEqual(failure.exception.status, "timeout")
        self.assertIsNone(failure.exception.http_status)
        post.assert_not_awaited()
        self.assertEqual(set(self.guard._models), {"primary-test"})
        self.assertEqual(len(self.guard._models["primary-test"][0]), 1)
        self.assertEqual(self.guard._pending_count, 0)
        self.assertEqual(self.guard._waiters, {})

    async def test_outer_cancellation_cleans_waiter_without_reservation_or_input_storage(self):
        self.guard.reserve("primary-test", 1)
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock()) as post:
            task = asyncio.create_task(gemini.generate_text("private-input-never-in-queue"))
            await self.pending(1)
            state = repr((self.guard._models, self.guard._waiters))
            self.assertNotIn("private-input-never-in-queue", state)
            self.assertNotIn("offline-unit-placeholder", state)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        post.assert_not_awaited()
        self.assertEqual(len(self.guard._models["primary-test"][0]), 1)
        self.assertEqual(self.guard._pending_count, 0)

    async def test_cancellation_when_slot_becomes_ready_still_does_not_reserve(self):
        self.guard.reserve("model", 1)
        waiting = asyncio.create_task(self.guard.wait("model", 1))
        await self.pending(1)
        self.advance(60)
        waiting.cancel()  # Slot available, but waiter has not resumed/reserved.
        with self.assertRaises(asyncio.CancelledError):
            await waiting
        self.assertEqual(list(self.guard._models["model"][0]), [100.0])
        self.assertEqual(self.guard._pending_count, 0)

    async def test_pending_capacity_is_32_across_models_and_never_reserves_failed_admission(self):
        self.guard.reserve("one", 1)
        self.guard.reserve("two", 1)
        tasks = [asyncio.create_task(self.guard.wait("one" if index % 2 else "two", 1))
                 for index in range(32)]
        try:
            await self.pending(32)
            with self.assertRaises(gemini.GeminiError) as failure:
                await self.guard.wait("one", 1)
            self.assertEqual(failure.exception.status, "rate_limited")
            self.assertIsNone(failure.exception.http_status)
            self.assertEqual(self.guard._pending_count, 32)
            self.assertEqual(sum(len(record[0]) for record in self.guard._models.values()), 2)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertEqual(self.guard._pending_count, 0)
        self.assertEqual(self.guard._waiters, {})

    async def test_cancelled_head_does_not_block_next_and_newcomer_cannot_jump_fifo(self):
        self.guard.reserve("model", 1)
        order = []
        async def reserve(number):
            await self.guard.wait("model", 1)
            order.append(number)
        first = asyncio.create_task(reserve(1))
        second = asyncio.create_task(reserve(2))
        await self.pending(2)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        third = asyncio.create_task(reserve(3))
        await self.pending(2)
        self.advance(60)
        await self.pending(1)
        self.assertEqual(order, [2])
        self.assertEqual(len(self.guard._models["model"][0]), 1)
        self.advance(60)
        await asyncio.gather(second, third)
        self.assertEqual(order, [2, 3])
        self.assertEqual(self.guard._pending_count, 0)

    async def test_cooldown_aborts_waiters_immediately_without_waiting_retry_or_fallback(self):
        self.guard.reserve("primary-test", 1)
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock()) as post:
            waiting = asyncio.create_task(gemini.generate_text("fixed control"))
            await self.pending(1)
            self.guard.pause("primary-test", 120)
            with self.assertRaises(gemini.GeminiError) as failure:
                await waiting
            with self.assertRaises(gemini.GeminiError) as next_failure:
                await gemini.generate_text("fixed control")
        self.assertEqual(failure.exception.status, "rate_limited")
        self.assertEqual(next_failure.exception.status, "rate_limited")
        post.assert_not_awaited()
        self.assertEqual(set(self.guard._models), {"primary-test"})
        self.assertEqual(self.guard._pending_count, 0)

    async def test_http_429_cancels_local_waiting_without_second_send_or_model_rotation(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def transport(*_args, **_kwargs):
            entered.set()
            await release.wait()
            return httpx.Response(429, headers={"retry-after": "120"})
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=transport)) as post:
            active = asyncio.create_task(gemini.generate_text("first fixed control"))
            await entered.wait()
            waiting = asyncio.create_task(gemini.generate_text("second fixed control"))
            await self.pending(1)
            release.set()
            results = await asyncio.gather(active, waiting, return_exceptions=True)
        self.assertTrue(all(isinstance(result, gemini.GeminiError) and result.status == "rate_limited"
                            for result in results))
        self.assertEqual(results[0].http_status, 429)
        self.assertIsNone(results[1].http_status)
        post.assert_awaited_once()
        self.assertEqual(set(self.guard._models), {"primary-test"})
        self.assertEqual(self.guard._models["primary-test"][1], self.now + 120)
        self.assertEqual(len(self.guard._models["primary-test"][0]), 1)
        self.assertEqual(self.guard._pending_count, 0)

    async def test_pause_from_another_thread_wakes_owned_loop_and_cleans_queue(self):
        self.guard.reserve("model", 1)
        pending = asyncio.create_task(self.guard.wait("model", 1))
        await self.pending(1)
        await asyncio.to_thread(self.guard.pause, "model", 60)
        with self.assertRaises(gemini.GeminiError) as failure:
            await pending
        self.assertEqual(failure.exception.status, "rate_limited")
        self.assertEqual(self.guard._pending_count, 0)

    async def test_model_capacity_stays_32_and_active_waiting_models_are_not_evicted(self):
        for index in range(32):
            self.guard.reserve(f"model-{index}", 1)
        waiting = asyncio.create_task(self.guard.wait("model-0", 1))
        await self.pending(1)
        try:
            with self.assertRaises(gemini.GeminiError):
                await self.guard.wait("another-model", 1)
            self.assertEqual(len(self.guard._models), 32)
            self.now += 60
            await self.guard.wait("another-model", 1)
            self.assertEqual(set(self.guard._models), {"model-0", "another-model"})
            self.assertEqual(self.guard._pending_count, 1)
        finally:
            waiting.cancel()
            await asyncio.gather(waiting, return_exceptions=True)
        self.assertEqual(self.guard._pending_count, 0)


if __name__ == "__main__":
    unittest.main()
