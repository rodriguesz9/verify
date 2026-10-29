"""Skip identical web requests, never a different locale/operator or endpoint."""
import asyncio
from contextlib import ExitStack
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import pipeline
from app.core.serper_client import NewsSearch


TEXT = "O céu é como era e como foi."
OTHER = "O céu continua presente em outro relato literal."


class BaseSearchDeduplicationTests(unittest.IsolatedAsyncioTestCase):
    async def retrieve(self, *, recoveries=None, statuses=(), context=False):
        calls = []
        attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}

        async def search(query, **kwargs):
            calls.append((query, kwargs))
            value = statuses[len(calls) - 1] if len(calls) <= len(statuses) else "no_results"
            if isinstance(value, Exception):
                raise value
            return NewsSearch(status=value)

        context_tasks = ()
        if context:
            async def news():
                return NewsSearch([{"link": "https://www.bbc.com/news/a-story", "title": TEXT}])
            context_tasks = (asyncio.create_task(news()),)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}))
            stack.enter_context(patch.object(pipeline, "research_enabled", return_value=False))
            stack.enter_context(patch.object(pipeline, "search_web", new=AsyncMock(side_effect=search)))
            collect = stack.enter_context(patch.object(pipeline, "collect_source_attribution",
                new=AsyncMock(return_value=attribution)))
            stack.enter_context(patch.object(pipeline, "collect_official_copom_record",
                new=AsyncMock(return_value={"status": "not_requested"})))
            stack.enter_context(patch.object(pipeline, "usable_source_families", return_value=set()))
            if recoveries is not None:
                stack.enter_context(patch.object(pipeline, "_source_recovery_queries", return_value=recoveries))
            result = await pipeline._retrieve_source_attribution(TEXT, [TEXT], None,
                context_news_tasks=context_tasks)
        return result, calls, collect

    async def test_actual_unknown_topic_keeps_distinct_curated_query_without_repeating_literal(self):
        result, calls, collect = await self.retrieve()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], (TEXT, {}))
        self.assertNotEqual(calls[1][0], TEXT)
        self.assertIn(pipeline.SOURCE_SITE_FILTER, calls[1][0])
        coverage = result["coverage"]
        self.assertEqual(coverage["base_skipped_duplicate_query_count"], 1)
        self.assertEqual(len(coverage["search_queries"]), 2)
        self.assertEqual(coverage["max_search_queries"], 3)
        self.assertEqual(coverage["retrieval_deadline_seconds"], 45)
        self.assertTrue(all(call.args[0] == TEXT for call in collect.await_args_list))
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["_documents"], [])
        self.assertNotIn("verdict", result)

    async def test_only_transport_edge_whitespace_is_equivalent(self):
        result, calls, _ = await self.retrieve(recoveries=[
            ("  " + TEXT + "  ", "duplicate"), (OTHER, "distinct")])
        self.assertEqual([query for query, _ in calls], [TEXT, OTHER])
        self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 1)

    async def test_internal_spacing_case_quotes_and_operators_remain_distinct(self):
        for first, second in (("Alfa OR Beta estudo público", "Alfa or Beta estudo público"),
                              ('"Alfa Beta" estudo público', 'Alfa Beta estudo público'),
                              ("Alfa  Beta estudo público", "Alfa Beta estudo público")):
            with self.subTest(first=first, second=second):
                result, calls, _ = await self.retrieve(recoveries=[(first, "first"), (second, "second")])
                self.assertEqual([query for query, _ in calls], [TEXT, first, second])
                self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 0)

    async def test_same_query_in_a_different_locale_remains_a_distinct_request(self):
        result, calls, _ = await self.retrieve(recoveries=[
            (TEXT, "literal_topic_anchors_bilingual_editorial_sources")])
        self.assertEqual(calls, [(TEXT, {}), (TEXT, {"language": "en"})])
        self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 0)

    async def test_two_identical_recoveries_spend_one_request_without_a_replacement_slot(self):
        result, calls, _ = await self.retrieve(recoveries=[(OTHER, "first"), (OTHER, "second")])
        self.assertEqual([query for query, _ in calls], [TEXT, OTHER])
        self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 1)
        self.assertEqual(len(result["coverage"]["search_queries"]), 2)

    async def test_timeout_is_preserved_and_does_not_allow_retrying_the_same_query(self):
        result, calls, _ = await self.retrieve(statuses=("timeout", "success"))
        self.assertEqual(len(calls), 2)
        coverage = result["coverage"]
        self.assertEqual(coverage["search_queries"][0]["status"], "timeout")
        self.assertEqual(coverage["search_queries"][1]["status"], "success")
        self.assertEqual(coverage["base_skipped_duplicate_query_count"], 1)

    async def test_quota_auth_or_unknown_error_still_stops_recovery(self):
        for failure in ("rate_limited", "not_configured", "invalid_configuration", "error", "invalid_response"):
            with self.subTest(failure=failure):
                result, calls, _ = await self.retrieve(statuses=(failure,))
                self.assertEqual(calls, [(TEXT, {})])
                self.assertEqual(result["coverage"]["search_queries"], [
                    {"method": "whole_literal_claim", "status": failure}])
                self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 0)

    async def test_skip_count_survives_a_later_recovery_exception(self):
        result, calls, _ = await self.retrieve(statuses=("no_results", RuntimeError("offline control")))
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 1)
        self.assertEqual(result["coverage"]["recovery_status"], "timeout_or_error")
        self.assertEqual(result["coverage"]["search_queries"], [
            {"method": "whole_literal_claim", "status": "no_results"}])

    async def test_existing_news_endpoint_results_are_still_joined_as_separate_leads(self):
        result, calls, _ = await self.retrieve(context=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["coverage"]["context_news_recovery"], {
            "status": "success", "awaited_query_count": 1,
            "candidate_url_count": 1, "decision_role": "retrieval_leads_only"})
        self.assertEqual(result["coverage"]["base_skipped_duplicate_query_count"], 1)
