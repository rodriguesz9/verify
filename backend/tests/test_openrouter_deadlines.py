"""Offline wall-clock bounds; no provider requests or factual accuracy claims."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from app.core import openrouter_service as router


def complete_response():
    return httpx.Response(200, json={"model": "vendor/control:free", "choices": [
        {"finish_reason": "stop", "message": {"content": "{}"}}], "usage": {"cost": 0}})


class OpenRouterDeadlineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "unit-test-not-secret",
            "OPENROUTER_ENABLED": "true", "OPENROUTER_MODEL": "openrouter/free",
            "OPENROUTER_FALLBACK_MODELS": "vendor/control:free"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = AsyncMock()
        self.client.__aenter__.return_value = self.client

    async def test_comparison_accepts_90_seconds_and_keeps_free_payload(self):
        self.client.post.return_value = complete_response()
        original_timeout = asyncio.timeout
        with patch.object(router, "_reserve_request") as reserve, \
             patch.object(router.httpx, "AsyncClient", return_value=self.client) as factory, \
             patch.object(router.asyncio, "timeout", wraps=original_timeout) as deadline:
            value = await router.generate("bounded control", timeout_seconds=90, max_tokens=9999)
        deadline.assert_called_once_with(90)
        factory.assert_called_once_with(timeout=90, trust_env=False, follow_redirects=False)
        reserve.assert_called_once()
        self.client.post.assert_awaited_once()
        self.assertEqual(value.model_name, "vendor/control:free")
        payload = self.client.post.await_args.kwargs["json"]
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertTrue(payload["provider"]["require_parameters"])
        self.assertTrue(all(price == 0 for price in payload["provider"]["max_price"].values()))

    async def test_default_deadline_remains_25_for_json_and_text(self):
        self.client.post.return_value = complete_response()
        original_timeout = asyncio.timeout
        for operation in (router.generate, router.generate_text):
            with self.subTest(operation=operation.__name__), \
                 patch.object(router, "_reserve_request"), \
                 patch.object(router.httpx, "AsyncClient", return_value=self.client) as factory, \
                 patch.object(router.asyncio, "timeout", wraps=original_timeout) as deadline:
                await operation("bounded control")
            deadline.assert_called_once_with(25)
            factory.assert_called_once_with(timeout=25, trust_env=False, follow_redirects=False)

    async def test_invalid_deadline_never_opens_client_or_charges_attempt(self):
        for value in (True, False, 0, -1, 91, float("inf"), float("nan"), "90", None):
            with self.subTest(value=value), patch.object(router, "_reserve_request") as reserve, \
                 patch.object(router.httpx, "AsyncClient") as factory:
                with self.assertRaises(router.OpenRouterError) as raised:
                    await router.generate("bounded control", timeout_seconds=value)
            self.assertEqual(raised.exception.status, "invalid_configuration")
            reserve.assert_not_called()
            factory.assert_not_called()

    async def test_free_fallback_shares_single_deadline_and_is_canceled_in_flight(self):
        canceled = asyncio.Event()
        original_timeout = asyncio.timeout

        async def response(*_args, **_kwargs):
            if self.client.post.await_count == 1:
                return httpx.Response(503)
            try:
                await asyncio.Future()
            finally:
                canceled.set()

        self.client.post.side_effect = response
        with patch.object(router, "_reserve_request") as reserve, \
             patch.object(router.httpx, "AsyncClient", return_value=self.client), \
             patch.object(router.asyncio, "timeout", wraps=original_timeout) as deadline:
            with self.assertRaises(router.OpenRouterError) as raised:
                await router.generate("bounded control", timeout_seconds=.04)
        self.assertEqual(raised.exception.status, "timeout")
        self.assertTrue(canceled.is_set())
        deadline.assert_called_once_with(.04)
        self.assertEqual(reserve.call_count, 2)
        self.assertEqual(self.client.post.await_count, 2)
        self.client.__aexit__.assert_awaited_once()

    async def test_client_initialization_is_inside_same_deadline_before_any_charge(self):
        canceled = asyncio.Event()

        async def enter():
            try:
                await asyncio.Future()
            finally:
                canceled.set()

        self.client.__aenter__.side_effect = enter
        with patch.object(router, "_reserve_request") as reserve, \
             patch.object(router.httpx, "AsyncClient", return_value=self.client):
            with self.assertRaises(router.OpenRouterError) as raised:
                await router.generate("bounded control", timeout_seconds=.01)
        self.assertEqual(raised.exception.status, "timeout")
        self.assertTrue(canceled.is_set())
        reserve.assert_not_called()
        self.client.post.assert_not_awaited()

    async def test_external_cancel_propagates_without_fallback_or_detached_request(self):
        started, canceled = asyncio.Event(), asyncio.Event()

        async def response(*_args, **_kwargs):
            started.set()
            try:
                await asyncio.Future()
            finally:
                canceled.set()

        self.client.post.side_effect = response
        with patch.object(router, "_reserve_request") as reserve, \
             patch.object(router.httpx, "AsyncClient", return_value=self.client):
            task = asyncio.create_task(router.generate("bounded control", timeout_seconds=90))
            try:
                await asyncio.wait_for(started.wait(), timeout=1)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertTrue(canceled.is_set())
        reserve.assert_called_once()
        self.client.post.assert_awaited_once()
        self.client.__aexit__.assert_awaited_once()

    async def test_quota_response_never_rotates_or_retries(self):
        for status in (402, 429):
            self.client.post.reset_mock()
            self.client.post.return_value = httpx.Response(status)
            with self.subTest(status=status), patch.object(router, "_reserve_request") as reserve, \
                 patch.object(router, "_cooldown_until", 0.0), \
                 patch.object(router.httpx, "AsyncClient", return_value=self.client):
                with self.assertRaises(router.OpenRouterError) as raised:
                    await router.generate("bounded control", timeout_seconds=90)
                self.assertGreater(router._cooldown_until, 0)
            self.assertEqual(raised.exception.status, "rate_limited")
            reserve.assert_called_once()
            self.client.post.assert_awaited_once()
