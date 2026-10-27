"""Technical planner recovery must not repeat rejected or protected operations."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import gemini_client, openrouter_service
from app.services import source_research as research


TEXT = "A missão DART da NASA colidiu intencionalmente com Dimorphos em 26 de setembro de 2022."
QUERY = {"query": "NASA DART Dimorphos intentional impact date", "source_group": "editorial"}
PLAN = {"queries": [QUERY], "lead_ids": []}
PRIVATE_MARKER = "untrusted-output-do-not-export-7823"


class SourceResearchRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"SERPERAPI_KEY": "offline-test", "GEMINI_API_KEY": "offline-test",
            "OPENROUTER_API_KEY": "offline-test", "OPENROUTER_ENABLED": "true"}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    async def run_plan(self, primary, alternate=None, *, leads=(), budget=2):
        first = AsyncMock(side_effect=primary) if isinstance(primary, BaseException) else AsyncMock(return_value=primary)
        second = AsyncMock(side_effect=alternate) if isinstance(alternate, BaseException) else AsyncMock(
            return_value=json.dumps(PLAN) if alternate is None else alternate)
        with patch.object(gemini_client, "generate_text", first), patch.object(openrouter_service, "generate", second):
            result = await research.plan_source_research(TEXT, list(leads), [], {}, timeout_seconds=budget)
        self.assertNotIn(PRIVATE_MARKER, str(result))
        return result, first, second

    async def test_bad_json_and_schema_use_one_existing_alternate_without_forwarding_output(self):
        bad = (PRIVATE_MARKER, "[]", '{"queries":[]}',
            json.dumps({"queries": "invalid", "lead_ids": []}),
            json.dumps({"queries": [123], "lead_ids": []}),
            json.dumps({"queries": [], "lead_ids": [123]}),
            json.dumps({**PLAN, "verdict": "invented"}))
        for raw in bad:
            with self.subTest(raw=raw):
                result, first, second = await self.run_plan(raw)
                self.assertEqual(result["queries"], [QUERY])
                self.assertEqual(result["coverage"]["status"], "success")
                first.assert_awaited_once()
                second.assert_awaited_once()
                primary = result["coverage"]["provider_coverage"]["gemini"]
                self.assertEqual(primary["status"], "invalid_response")
                self.assertEqual(primary["failure_kind"], "invalid_research_response")
                self.assertEqual(primary["response_issue"], "invalid_json" if raw == PRIVATE_MARKER else "invalid_schema")
                self.assertEqual(first.call_args.args, second.call_args.args)
                self.assertNotIn(PRIVATE_MARKER, second.call_args.args[0])
                self.assertLessEqual(first.call_args.kwargs["timeout_seconds"], 1)
                self.assertLessEqual(second.call_args.kwargs["timeout_seconds"], 2)

    async def test_second_invalid_envelope_ends_after_two_attempts_with_both_failures_preserved(self):
        result, first, second = await self.run_plan(PRIVATE_MARKER, "[]")
        self.assertEqual(result["coverage"]["status"], "invalid_response")
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["leads"], [])
        for provider, issue in (("gemini", "invalid_json"), ("openrouter", "invalid_schema")):
            coverage = result["coverage"]["provider_coverage"][provider]
            self.assertEqual(coverage["status"], "invalid_response")
            self.assertEqual(coverage["response_issue"], issue)
        self.assertEqual(first.await_count + second.await_count, 2)

    async def test_semantically_rejected_queries_and_ids_never_trigger_another_plan(self):
        invalid = (
            {"queries": [], "lead_ids": ["invented"]},
            {"queries": [], "lead_ids": ["l1", "l1"]},
            {"queries": [{**QUERY, "query": "DART NASA https://example.org/secret"}], "lead_ids": []},
            {"queries": [{**QUERY, "query": "DART NASA site:example.org"}], "lead_ids": []},
            {"queries": [{**QUERY, "query": "Um assunto diferente sobre culinária e receitas"}], "lead_ids": []},
            {"queries": [{**QUERY, "query": "DART NASA\n" + PRIVATE_MARKER}], "lead_ids": []},
        )
        for plan in invalid:
            with self.subTest(plan=plan):
                result, first, second = await self.run_plan(json.dumps(plan))
                first.assert_awaited_once()
                second.assert_not_awaited()
                self.assertEqual(result["coverage"]["status"], "invalid_response")
                self.assertEqual(result["coverage"]["provider_coverage"]["gemini"]["failure_kind"],
                    "rejected_research_operation")

    async def test_valid_empty_plan_remains_final(self):
        result, first, second = await self.run_plan('{"queries":[],"lead_ids":[]}')
        self.assertEqual(result["coverage"]["status"], "success")
        self.assertEqual(result["queries"], [])
        first.assert_awaited_once()
        second.assert_not_awaited()

    async def test_valid_partial_plan_preserves_good_operations_without_another_provider(self):
        for plan in ({"queries": [QUERY, 123], "lead_ids": []},
                     {"queries": [QUERY], "lead_ids": ["invented"]}):
            with self.subTest(plan=plan):
                result, first, second = await self.run_plan(json.dumps(plan))
                self.assertEqual(result["coverage"]["status"], "partial")
                self.assertEqual(result["queries"], [QUERY])
                self.assertEqual(result["leads"], [])
                self.assertEqual(result["coverage"]["rejected_operation_count"], 1)
                first.assert_awaited_once()
                second.assert_not_awaited()

    async def test_protection_or_cost_issue_never_relays_to_another_provider(self):
        for issue in ("content_blocked", "unexpected_cost"):
            with self.subTest(issue=issue):
                result, first, second = await self.run_plan(gemini_client.GeminiError(
                    PRIVATE_MARKER, "invalid_response", response_issue=issue))
                second.assert_not_awaited()
                self.assertEqual(result["coverage"]["status"], "invalid_response")
                self.assertEqual(result["coverage"]["provider_coverage"]["gemini"]["response_issue"], issue)
                first.assert_awaited_once()

    async def test_invalid_config_unsupported_or_large_input_never_relays(self):
        for status in ("invalid_configuration", "input_too_large", "unsupported"):
            with self.subTest(status=status):
                result, first, second = await self.run_plan(gemini_client.GeminiError(PRIVATE_MARKER, status))
                second.assert_not_awaited()
                self.assertEqual(result["coverage"]["status"], status)
                first.assert_awaited_once()

    async def test_alternate_block_after_technical_failure_is_not_reported_as_success(self):
        result, first, second = await self.run_plan(PRIVATE_MARKER,
            openrouter_service.OpenRouterError("invalid_response", PRIVATE_MARKER, response_issue="content_blocked"))
        self.assertEqual(result["coverage"]["status"], "invalid_response")
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["coverage"]["provider_coverage"]["openrouter"]["response_issue"], "content_blocked")
        self.assertEqual(first.await_count + second.await_count, 2)

    async def test_without_an_alternate_bad_json_remains_invalid_response(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            result, first, second = await self.run_plan(PRIVATE_MARKER)
        self.assertEqual(result["coverage"]["status"], "invalid_response")
        self.assertEqual(set(result["coverage"]["provider_coverage"]), {"gemini"})
        first.assert_awaited_once()
        second.assert_not_awaited()

    async def test_oversized_nontext_or_deep_json_is_discarded_before_alternate(self):
        for raw in (" " * 30001, ["not text"], "[" * 2000 + "]" * 2000):
            with self.subTest(raw_type=type(raw).__name__, size=len(raw)):
                result, first, second = await self.run_plan(raw)
                self.assertEqual(result["queries"], [QUERY])
                self.assertEqual(result["coverage"]["status"], "success")
                self.assertEqual(result["coverage"]["provider_coverage"]["gemini"]["status"], "invalid_response")
                first.assert_awaited_once()
                second.assert_awaited_once()

    async def test_openrouter_only_configuration_uses_same_whitespace_rule_as_enablement(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_ENABLED": " true "}):
            result, first, second = await self.run_plan(PRIVATE_MARKER)
        first.assert_not_awaited()
        second.assert_awaited_once()
        self.assertEqual(result["queries"], [QUERY])
        self.assertEqual(set(result["coverage"]["provider_coverage"]), {"openrouter"})

    async def test_cancellation_does_not_launch_an_alternate(self):
        first, second = AsyncMock(side_effect=asyncio.CancelledError), AsyncMock()
        with patch.object(gemini_client, "generate_text", first), patch.object(openrouter_service, "generate", second):
            with self.assertRaises(asyncio.CancelledError):
                await research.plan_source_research(TEXT, [], [], {}, timeout_seconds=2)
        first.assert_awaited_once()
        second.assert_not_awaited()
