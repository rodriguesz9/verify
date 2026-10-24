"""Shared opportunity/cancellation, not a factual accuracy benchmark."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from app.core.gemini_client import GeminiError
from app.services import source_corroboration as sources


PROMPT = json.dumps({"claims": [{"claim_id": "c1", "claim": "Controle literal completo."}],
    "sources": [{"source_id": "s1", "passages": [{"excerpt_id": "s1:e1", "quote": "Controle literal completo.",
                                                "context": "Controle literal completo."}]}]})
ANSWER = json.dumps({"claims": [{"claim_id": "c1", "source_reviews": [{"source_id": "s1",
    "assessment": "insufficient", "evidence": []}]}]})


def coverage():
    return {"gemini": {"status": "not_requested"}, "openrouter": {"status": "not_requested"}}


class FairComparisonDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_providers_each_receive_up_to_120_without_extending_whole_deadline(self):
        with patch.object(sources.gemini_client, "generate_text", new=AsyncMock(side_effect=GeminiError("Unavailable", "unavailable"))) as first, \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock(return_value=ANSWER)) as second:
            raw, result, status = await sources._compare(PROMPT, coverage(), timeout_seconds=240)
        self.assertEqual(raw, ANSWER)
        self.assertEqual(status, "success")
        self.assertTrue(119 < first.await_args.kwargs["timeout_seconds"] <= 120)
        self.assertEqual(second.await_args.kwargs["timeout_seconds"], 120)
        self.assertEqual(result["gemini"]["status"], "unavailable")

    async def test_hanging_primary_is_joined_and_remaining_half_reaches_alternate(self):
        cleaned = asyncio.Event()
        async def first(*args, **kwargs):
            try:
                await asyncio.Future()
            finally:
                cleaned.set()
        async def second(*args, **kwargs):
            self.assertTrue(cleaned.is_set())
            self.assertTrue(0 < kwargs["timeout_seconds"] <= .1)
            await asyncio.sleep(.01)
            return ANSWER
        with patch.object(sources.gemini_client, "generate_text", new=AsyncMock(side_effect=first)), \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock(side_effect=second)) as fallback:
            raw, result, status = await sources._compare(PROMPT, coverage(), timeout_seconds=.2)
        self.assertEqual(status, "success")
        self.assertEqual(result["gemini"]["status"], "timeout")
        fallback.assert_awaited_once()

    async def test_successful_insufficient_review_never_shops_another_model_for_a_verdict(self):
        with patch.object(sources.gemini_client, "generate_text", new=AsyncMock(return_value=ANSWER)), \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock()) as fallback:
            _, _, status = await sources._compare(PROMPT, coverage(), timeout_seconds=.2)
        self.assertEqual(status, "success")
        fallback.assert_not_awaited()

    async def test_zero_remaining_time_starts_no_provider(self):
        with patch.object(sources.gemini_client, "generate_text", new=AsyncMock()) as first, \
             patch.object(sources.openrouter_service, "generate", new=AsyncMock()) as second:
            _, _, status = await sources._compare(PROMPT, coverage(), timeout_seconds=0)
        self.assertEqual(status, "timeout")
        first.assert_not_awaited()
        second.assert_not_awaited()
