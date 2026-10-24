"""Offline transport resilience. No quota bypass, factual votes or real HTTP."""
import asyncio
import os
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import httpx

from app.core import gemini_client as gemini
from app.core import openrouter_service as router


def response(provider, *, complete=True):
    if provider == "gemini":
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP" if complete else "MAX_TOKENS",
            "content": {"parts": [{"text": '{"answer":"insufficient"}'}]}}]})
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop" if complete else "length",
        "message": {"content": '{"answer":"insufficient"}'}}], "usage": {"cost": 0}})


class ExplicitFallbackOpportunityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "GEMINI_API_KEY": "offline-placeholder", "GEMINI_MODEL_NAME": "primary-test",
            "GEMINI_FALLBACK_MODELS": "alternate-test", "GEMINI_LOCAL_ADMISSION_ENABLED": "false",
            "OPENROUTER_API_KEY": "offline-placeholder", "OPENROUTER_ENABLED": "true",
            "OPENROUTER_MODEL": "vendor/primary:free", "OPENROUTER_FALLBACK_MODELS": "vendor/alternate:free",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def setup_provider(self, provider, stack):
        module = gemini if provider == "gemini" else router
        client = AsyncMock()
        client.__aenter__.return_value = client
        stack.enter_context(patch.object(module.httpx, "AsyncClient", return_value=client))
        if provider == "gemini":
            reserve = stack.enter_context(patch.object(module, "_reserve_request", new=AsyncMock()))
        else:
            reserve = stack.enter_context(patch.object(module, "_reserve_request"))
        stack.enter_context(patch.object(router, "_cooldown_until", 0.0))
        operation = gemini.generate_text if provider == "gemini" else router.generate
        error = gemini.GeminiError if provider == "gemini" else router.OpenRouterError
        return client, reserve, operation, error

    async def test_hanging_primary_is_canceled_then_explicit_alternate_can_respond(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider), ExitStack() as stack:
                client, reserve, operation, _error = self.setup_provider(provider, stack)
                canceled = asyncio.Event()

                async def post(*_args, **_kwargs):
                    if client.post.await_count == 1:
                        try:
                            await asyncio.Future()
                        finally:
                            canceled.set()
                    self.assertTrue(canceled.is_set())
                    return response(provider)

                client.post.side_effect = post
                value = await operation("fixed input", timeout_seconds=.12)
                self.assertEqual(str(value), '{"answer":"insufficient"}')
                self.assertEqual(value.model_name, "alternate-test" if provider == "gemini" else "vendor/alternate:free")
                self.assertEqual(client.post.await_count, 2)
                self.assertEqual(reserve.call_count, 2)
                client.__aexit__.assert_awaited_once()

    async def test_both_hanging_attempts_are_bounded_joined_and_charged_once_each(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider), ExitStack() as stack:
                client, reserve, operation, error = self.setup_provider(provider, stack)
                canceled = []

                async def post(*_args, **_kwargs):
                    attempt = client.post.await_count
                    try:
                        await asyncio.Future()
                    finally:
                        canceled.append(attempt)

                client.post.side_effect = post
                with self.assertRaises(error) as raised:
                    await operation("fixed input", timeout_seconds=.08)
                self.assertEqual(raised.exception.status, "timeout")
                self.assertEqual(canceled, [1, 2])
                self.assertEqual(reserve.call_count, 2)
                self.assertEqual(client.post.await_count, 2)
                client.__aexit__.assert_awaited_once()

    async def test_fast_transient_failure_releases_unused_share_to_alternate(self):
        for provider in ("gemini", "openrouter"):
            for failure in (httpx.ReadTimeout("private-input"), httpx.ConnectError("private-input"),
                            httpx.RemoteProtocolError("private-input"),
                            httpx.Response(500), httpx.Response(502), httpx.Response(503), httpx.Response(504)):
                with self.subTest(provider=provider, failure=type(failure).__name__), ExitStack() as stack:
                    client, reserve, operation, _error = self.setup_provider(provider, stack)
                    original = asyncio.timeout_at
                    deadlines = []

                    def timeout_at(value):
                        deadlines.append(value)
                        return original(value)

                    stack.enter_context(patch.object(asyncio, "timeout_at", side_effect=timeout_at))
                    client.post.side_effect = [failure, response(provider)]
                    value = await operation("fixed input", timeout_seconds=90)
                    self.assertEqual(str(value), '{"answer":"insufficient"}')
                    self.assertEqual(reserve.call_count, 2)
                    self.assertEqual(len(deadlines), 2)
                    self.assertTrue(44 < deadlines[1] - deadlines[0] <= 45.1)

    async def test_auth_permission_payment_quota_and_request_errors_never_rotate(self):
        for provider in ("gemini", "openrouter"):
            for status in (400, 401, 402, 403, 409, 422, 429):
                with self.subTest(provider=provider, status=status), ExitStack() as stack:
                    client, reserve, operation, error = self.setup_provider(provider, stack)
                    client.post.return_value = httpx.Response(status)
                    with self.assertRaises(error):
                        await operation("fixed input", timeout_seconds=90)
                    reserve.assert_called_once()
                    client.post.assert_awaited_once()

    async def test_complete_insufficient_response_and_incomplete_response_never_shop_models(self):
        for provider in ("gemini", "openrouter"):
            for complete in (True, False):
                with self.subTest(provider=provider, complete=complete), ExitStack() as stack:
                    client, reserve, operation, error = self.setup_provider(provider, stack)
                    client.post.return_value = response(provider, complete=complete)
                    if complete:
                        self.assertEqual(str(await operation("fixed input")), '{"answer":"insufficient"}')
                    else:
                        with self.assertRaises(error) as raised:
                            await operation("fixed input")
                        self.assertEqual(raised.exception.status, "invalid_response")
                    reserve.assert_called_once()
                    client.post.assert_awaited_once()

    async def test_single_model_keeps_whole_deadline_without_implicit_alternate(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider), ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, {"GEMINI_FALLBACK_MODELS": "", "OPENROUTER_FALLBACK_MODELS": ""}))
                client, reserve, operation, _error = self.setup_provider(provider, stack)
                client.post.return_value = response(provider)
                original = asyncio.timeout_at
                deadlines = []
                started = asyncio.get_running_loop().time()

                def timeout_at(value):
                    deadlines.append(value)
                    return original(value)

                stack.enter_context(patch.object(asyncio, "timeout_at", side_effect=timeout_at))
                await operation("fixed input", timeout_seconds=90)
                self.assertEqual(len(deadlines), 1)
                self.assertTrue(89 < deadlines[0] - started < 90.1)
                reserve.assert_called_once()
                client.post.assert_awaited_once()

    async def test_external_cancel_does_not_turn_into_timeout_or_start_alternate(self):
        for provider in ("gemini", "openrouter"):
            with self.subTest(provider=provider), ExitStack() as stack:
                client, reserve, operation, _error = self.setup_provider(provider, stack)
                started, canceled = asyncio.Event(), asyncio.Event()

                async def post(*_args, **_kwargs):
                    started.set()
                    try:
                        await asyncio.Future()
                    finally:
                        canceled.set()

                client.post.side_effect = post
                task = asyncio.create_task(operation("fixed input", timeout_seconds=90))
                await asyncio.wait_for(started.wait(), timeout=1)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertTrue(canceled.is_set())
                reserve.assert_called_once()
                client.post.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
