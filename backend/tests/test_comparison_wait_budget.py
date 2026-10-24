"""Bounded comparison transport controls, never factual accuracy tests."""
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from app.core import openrouter_service as router
from app.services.source_corroboration import crosscheck_timeout_seconds


class ComparisonWaitBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_comparison_can_use_4096_tokens_and_45_seconds_free_only(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = httpx.Response(200, json={"model": "vendor/control:free",
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}], "usage": {"cost": 0}})
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "unit-test-not-secret",
                "OPENROUTER_ENABLED": "true", "OPENROUTER_MODEL": "openrouter/free",
                "OPENROUTER_FALLBACK_MODELS": ""}), \
             patch.object(router, "_reserve_request") as reserve, \
             patch.object(router.httpx, "AsyncClient", return_value=client) as factory:
            await router.generate("bounded matrix", max_tokens=9999, timeout_seconds=45)
        factory.assert_called_once_with(timeout=45, trust_env=False, follow_redirects=False)
        reserve.assert_called_once()
        client.post.assert_awaited_once()
        payload = client.post.await_args.kwargs["json"]
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertEqual(payload["model"], "openrouter/free")
        self.assertTrue(payload["provider"]["require_parameters"])
        self.assertTrue(all(value == 0 for value in payload["provider"]["max_price"].values()))

    async def test_invalid_timeout_never_reserves_or_sends(self):
        for timeout in (True, 0, -1, 121, float("nan"), float("inf"), "45", None):
            with self.subTest(timeout=timeout), patch.dict(os.environ, {
                    "OPENROUTER_API_KEY": "unit-test-not-secret", "OPENROUTER_ENABLED": "true",
                    "OPENROUTER_MODEL": "openrouter/free", "OPENROUTER_FALLBACK_MODELS": ""}), \
                 patch.object(router, "_reserve_request") as reserve, \
                 patch.object(router.httpx, "AsyncClient") as factory:
                with self.assertRaises(router.OpenRouterError) as error:
                    await router.generate("matrix", timeout_seconds=timeout)
                self.assertEqual(error.exception.status, "invalid_configuration")
                reserve.assert_not_called()
                factory.assert_not_called()

    def test_crosscheck_shared_default_and_upper_bound_are_240_seconds(self):
        with patch.dict(os.environ):
            os.environ.pop("SOURCE_CROSSCHECK_TIMEOUT_SECONDS", None)
            self.assertEqual(crosscheck_timeout_seconds(), 240)
        for configured, expected in (("10", 10), ("45", 45), ("60", 60), ("90", 90), ("91", 91), ("180", 180), ("181", 181), ("240", 240), ("241", 240), ("0", 240)):
            with self.subTest(configured=configured), patch.dict(os.environ, {"SOURCE_CROSSCHECK_TIMEOUT_SECONDS": configured}):
                self.assertEqual(crosscheck_timeout_seconds(), expected)
