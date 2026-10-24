"""A timed-out query is visible, not a blanket veto on different queries."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import pipeline
from app.core.serper_client import NewsSearch


TEXT = "A Organização Mundial da Saúde classificou Zeta-31 como pandemia em 10 de abril de 2001."


class TransientSearchRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, statuses):
        responses = [NewsSearch(status=status) for status in statuses]
        attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}
        plan = {"queries": [], "leads": [], "coverage": {"status": "success", "planned_query_count": 0}}
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}), \
             patch.object(pipeline, "research_enabled", return_value=True), \
             patch.object(pipeline, "collect_official_copom_record", new=AsyncMock(return_value={"status": "not_requested"})), \
             patch.object(pipeline, "collect_source_attribution", new=AsyncMock(return_value=attribution)), \
             patch.object(pipeline, "search_web", new=AsyncMock(side_effect=responses)) as searches, \
             patch.object(pipeline, "plan_source_research", new=AsyncMock(return_value=plan)) as planner:
            result = await pipeline._retrieve_source_attribution(TEXT, [TEXT], None)
        return result, searches, planner

    async def test_timeout_does_not_cancel_remaining_different_queries_or_planner(self):
        for statuses in (("timeout", "success", "success", "success", "success"),
                         ("success", "success", "timeout", "success", "success"),
                         ("success", "timeout", "timeout", "timeout", "success")):
            with self.subTest(statuses=statuses):
                result, searches, planner = await self.run_case(statuses)
                planner.assert_awaited_once()
                self.assertLessEqual(searches.await_count, 5)
                queries = [call.args[0] for call in searches.await_args_list]
                self.assertEqual(len(queries), len(set(queries)))
                self.assertEqual(result["coverage"]["search_queries"][0]["status"], statuses[0])
                self.assertTrue(any(row["status"] == "timeout" for row in result["coverage"]["search_queries"]))
                self.assertEqual(result["coverage"]["max_search_queries"], 5)
                self.assertEqual(result["coverage"]["retrieval_deadline_seconds"], 105)

    async def test_quota_credentials_configuration_and_unclassified_errors_still_stop_search(self):
        for failure in ("rate_limited", "not_configured", "invalid_configuration", "error", "invalid_response"):
            for position in (0, 1, 2):
                with self.subTest(failure=failure, position=position):
                    statuses = ["success"] * position + [failure]
                    result, searches, planner = await self.run_case(statuses)
                    self.assertEqual(searches.await_count, position + 1)
                    planner.assert_not_awaited()
                    self.assertEqual(result["coverage"]["search_queries"][-1]["status"], failure)

    async def test_international_primary_and_editorial_use_declared_english_profile(self):
        _, searches, _ = await self.run_case(["success"] * 5)
        self.assertEqual([call.kwargs for call in searches.await_args_list[:3]],
                         [{}, {"language": "en"}, {"language": "en"}])
        self.assertEqual(pipeline._recovery_search_language("O IBGE informou o PIB em 2001.",
                         "literal_topic_anchors_primary_sources"), "pt-br")
        self.assertEqual(pipeline._recovery_search_language("O Instituto Zeta classificou o fenômeno em 2001.",
                         "literal_topic_anchors_primary_sources"), "pt-br")
