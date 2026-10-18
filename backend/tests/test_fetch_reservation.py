"""Offline cancellation controls for finite document-fetch reservations."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import collect_source_attribution


CLAIM = "A pesquisadora Aurora recebeu o prêmio Delta em 2021."


def page(url):
    return FetchedResource(f"<article><p>{CLAIM}</p></article>".encode(),
                           "text/html", url, "utf-8")


async def collect(urls, cache, limit):
    return await collect_source_attribution(CLAIM, [CLAIM],
        search_results=[{"link": url} for url in urls], include_documents=True,
        fetched_cache=cache, max_sources=limit)


class FetchReservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_batch_keeps_every_reservation_and_does_not_retry(self):
        urls = [f"https://example.test/pending-{index}" for index in range(2)]
        cache, started, stopped = {}, set(), set()
        all_started, pending = asyncio.Event(), asyncio.Event()

        async def fetch(url, **_kwargs):
            # Every slot is charged before the first request can start.
            self.assertEqual(set(cache), set(urls))
            started.add(url)
            if len(started) == len(urls):
                all_started.set()
            try:
                await pending.wait()
                self.fail("A cancelled fetch must not resume")
            finally:
                stopped.add(url)

        with patch("app.services.source_attribution.fetch_public_resource",
                   new=AsyncMock(side_effect=fetch)) as request:
            task = asyncio.create_task(collect(urls, cache, 2))
            await asyncio.wait_for(all_started.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(stopped, set(urls))
            self.assertEqual(cache, {url: {"failure": "error"} for url in urls})
            result = await collect([*urls, "https://example.test/not-started"], cache, 2)
            self.assertEqual(request.await_count, 2)
        self.assertEqual(result["coverage"]["new_fetch_count"], 0)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["coverage"]["failed_fetch_count"], 2)
        self.assertEqual(result["_documents"], [])
        self.assertEqual(result["matches"], [])

    async def test_completed_sibling_survives_later_batch_cancellation(self):
        fast, slow = "https://example.test/fast", "https://example.test/slow"
        cache = {}
        slow_started, slow_stopped, pending = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def fetch(url, **_kwargs):
            if url == fast:
                return page(url)
            slow_started.set()
            try:
                await pending.wait()
                self.fail("A cancelled fetch must not resume")
            finally:
                slow_stopped.set()

        async def fast_recorded():
            while "sentences" not in cache.get(fast, {}):
                await asyncio.sleep(0)

        with patch("app.services.source_attribution.fetch_public_resource",
                   new=AsyncMock(side_effect=fetch)) as request:
            task = asyncio.create_task(collect([fast, slow], cache, 2))
            await asyncio.wait_for(slow_started.wait(), 1)
            await asyncio.wait_for(fast_recorded(), 1)
            completed = cache[fast]
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(slow_stopped.is_set())
            self.assertIs(cache[fast], completed)
            self.assertEqual(cache[slow], {"failure": "error"})
            result = await collect([fast, slow], cache, 2)
            self.assertEqual(request.await_count, 2)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["coverage"]["fetched_count"], 1)
        self.assertEqual(result["coverage"]["failed_fetch_count"], 1)
        self.assertEqual([doc["url"] for doc in result["_documents"]], [fast])
        self.assertEqual([match["excerpt"] for match in result["matches"]], [CLAIM])

    async def test_child_cancellation_stops_siblings_before_propagating(self):
        cancelled, sibling = "https://example.test/cancelled", "https://example.test/sibling"
        cache, started = {}, set()
        all_started, sibling_stopped, pending = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def fetch(url, **_kwargs):
            started.add(url)
            if len(started) == 2:
                all_started.set()
            if url == cancelled:
                await all_started.wait()
                raise asyncio.CancelledError
            try:
                await pending.wait()
                self.fail("An abandoned sibling must not resume")
            finally:
                sibling_stopped.set()

        with patch("app.services.source_attribution.fetch_public_resource",
                   new=AsyncMock(side_effect=fetch)) as request:
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(collect([cancelled, sibling], cache, 2), 1)
            self.assertTrue(sibling_stopped.is_set())
            self.assertEqual(cache, {url: {"failure": "error"} for url in (cancelled, sibling)})
            await collect([cancelled, sibling], cache, 2)
            self.assertEqual(request.await_count, 2)

    async def test_http_failure_stays_charged_across_changed_recovery_leads(self):
        old = ["https://example.test/blocked", "https://example.test/old"]
        new = [f"https://example.test/recovery-{index}" for index in range(3)]
        cache = {}

        async def fetch(url, **_kwargs):
            if url == old[0]:
                raise HTTPException(403, "Offline blocked control")
            return page(url)

        with patch("app.services.source_attribution.fetch_public_resource",
                   new=AsyncMock(side_effect=fetch)) as request:
            first = await collect(old, cache, 2)
            second = await collect(new, cache, 3)
            third = await collect([*old, *new], cache, 3)
            attempted = [call.args[0] for call in request.await_args_list]
        self.assertEqual(attempted, [*old, new[0]])
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache[old[0]], {"failure": "blocked_or_unavailable"})
        self.assertEqual(first["coverage"]["failed_fetch_count"], 1)
        self.assertEqual(second["coverage"]["new_fetch_count"], 1)
        self.assertEqual(third["coverage"]["new_fetch_count"], 0)
        self.assertEqual(third["coverage"]["cumulative_fetch_attempt_count"], 3)


if __name__ == "__main__":
    unittest.main()
