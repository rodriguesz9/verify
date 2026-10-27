"""A missing alternate must not consume half the usable provider deadline."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import gemini_client, openrouter_service
from app.services import source_corroboration as sources
import test_source_review_generation_contract as controls


class ProviderTimeBudgetTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        selected, _, _, _ = sources._prepare_sources(controls.documents(), [controls.CLAIM], None)
        self.prompt = json.dumps({"claims": [{"claim_id": "c1", "claim": controls.CLAIM}],
            "sources": [{"source_id": item["source_id"], "passages": item["passages"]} for item in selected]})

    async def run_failed(self, keys, failure):
        coverage = {name: {"status": "not_requested"} for name in ('gemini', 'openrouter')}
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini", **keys}, clear=True), \
                patch.object(sources, '_gemini_comparison', new=AsyncMock(side_effect=failure)) as gemini, \
                patch.object(openrouter_service, 'generate', new=AsyncMock(side_effect=
                    openrouter_service.OpenRouterError('not_configured', 'Offline missing alternate'))) as router:
            result = await sources._compare(self.prompt, coverage, timeout_seconds=60)
        return result, gemini, router

    async def test_only_configured_gemini_receives_whole_shared_budget(self):
        result, gemini, router = await self.run_failed({'GEMINI_API_KEY': 'offline-control'}, TimeoutError())
        self.assertGreater(gemini.call_args.args[3], 59)
        self.assertLessEqual(gemini.call_args.args[3], 60)
        self.assertEqual(result[2], 'timeout')
        self.assertEqual(result[1]['gemini']['status'], 'timeout')
        self.assertEqual(result[1]['openrouter']['status'], 'not_configured')
        router.assert_awaited_once()

    async def test_disabled_alternate_with_a_key_does_not_take_time(self):
        result, gemini, _ = await self.run_failed({'GEMINI_API_KEY': 'offline-control',
            'OPENROUTER_API_KEY': 'offline-control', 'OPENROUTER_ENABLED': 'false'},
            gemini_client.GeminiError('Offline service unavailable', 'unavailable', 503))
        self.assertGreater(gemini.call_args.args[3], 59)
        self.assertEqual(result[2], 'unavailable')
        self.assertEqual(result[1]['gemini']['http_status'], 503)

    async def test_two_configured_providers_still_share_one_window(self):
        result, gemini, _ = await self.run_failed({'GEMINI_API_KEY': 'offline-control',
            'OPENROUTER_API_KEY': 'offline-control', 'OPENROUTER_ENABLED': 'true'}, TimeoutError())
        self.assertGreater(gemini.call_args.args[3], 29)
        self.assertLessEqual(gemini.call_args.args[3], 30)
        self.assertEqual(result[2], 'timeout')

    async def test_both_unconfigured_stay_unconfigured_without_invented_failure(self):
        result, _, _ = await self.run_failed({}, gemini_client.GeminiError('Offline absent key', 'not_configured'))
        self.assertEqual(result[2], 'not_configured')


class QAFreeModelArgumentsTests(unittest.TestCase):
    def test_verified_free_model_can_be_selected_without_other_budget_changes(self):
        from scripts.validation_ui_server import build_parser, validate_arguments, CAPS
        parser = build_parser()
        args = parser.parse_args(['--env-file', '/not-read.env', '--record-dir', '/not-written',
            '--gemini-model', 'gemini-3.5-flash-lite', '--media-model', 'gemini-3.5-flash-lite'])
        _, caps = validate_arguments(parser, args)
        self.assertEqual(caps['gemini'], CAPS['gemini'])
        self.assertEqual(caps['openrouter'], CAPS['openrouter'])
