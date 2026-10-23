"""Query-scope controls. Different filters are not different evidence families."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core.pipeline import _research_scope_plan, _research_query_text, _retrieve_source_attribution
from app.core.serper_client import NewsSearch
from app.services.source_queries import neutral_source_query


TEXT = "Em 18 de setembro de 2024, o Comitê Zeta reduziu a taxa de 10,75% para 10,50% ao ano."
FIRST = {"query": "Comitê Zeta decisão taxa setembro de 2024 resultado", "source_group": "primary"}
SECOND = {"query": "Comitê Zeta histórico decisões taxa em 2024", "source_group": "primary"}


class ResearchScopePlanTests(unittest.TestCase):
    def test_two_primary_or_open_queries_reserve_second_scope_for_editorial_without_rewriting_words(self):
        for group in ("primary", "any"):
            requested = [{**FIRST, "source_group": group}, {**SECOND, "source_group": group}]
            operations, audit = _research_scope_plan(TEXT, requested, [])
            self.assertEqual([item["query"] for item in operations], [FIRST["query"], SECOND["query"]])
            self.assertEqual([item["source_group"] for item in operations], [group, "editorial"])
            self.assertEqual(operations[1]["requested_source_group"], group)
            self.assertEqual(operations[1]["scope_change_reason"], "independent_family_gap")
            self.assertEqual(audit["scope_diversified_query_planned_count"], 1)
            self.assertEqual(audit["deterministic_gap_query_count"], 0)

    def test_already_editorial_plan_is_unchanged_and_one_editorial_query_does_not_force_another(self):
        for queries in ([{**FIRST, "source_group": "editorial"}],
                        [FIRST, {**SECOND, "source_group": "editorial"}]):
            operations, audit = _research_scope_plan(TEXT, queries, [])
            self.assertEqual([(item["query"], item["source_group"]) for item in operations],
                             [(item["query"], item["source_group"]) for item in queries])
            self.assertEqual(audit["scope_diversified_query_planned_count"], 0)
            self.assertEqual(audit["deterministic_gap_query_count"], 0)

    def test_single_primary_uses_one_free_original_neutral_editorial_slot(self):
        operations, audit = _research_scope_plan(TEXT, [FIRST], [TEXT])
        self.assertEqual(len(operations), 2)
        self.assertEqual(operations[1]["query"], neutral_source_query(TEXT, preserve_period=True))
        self.assertEqual(operations[1]["source_group"], "editorial")
        self.assertIsNone(operations[1]["requested_source_group"])
        self.assertEqual(operations[1]["query_origin"], "deterministic_original_neutral")
        self.assertEqual(audit["deterministic_gap_query_count"], 1)

    def test_empty_plan_uses_editorial_slot_but_never_repeats_completed_editorial_query(self):
        operations, _ = _research_scope_plan(TEXT, [], [TEXT])
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["source_group"], "editorial")
        neutral = neutral_source_query(TEXT, preserve_period=True)
        previous = [TEXT, _research_query_text(neutral, "editorial")]
        operations, audit = _research_scope_plan(TEXT, [], previous)
        self.assertEqual(operations[0]["source_group"], "any")
        self.assertEqual(operations[0]["query"], neutral)
        self.assertEqual(operations[0]["scope_change_reason"], "duplicate_editorial_query_already_executed")
        self.assertGreaterEqual(audit["skipped_duplicate_query_count"], 1)
        operations, audit = _research_scope_plan(TEXT, [], [*previous, neutral])
        self.assertEqual(operations, [])
        self.assertEqual(audit["deterministic_gap_query_count"], 0)

    def test_model_duplicates_invalid_operators_and_more_than_two_slots_never_create_unbounded_search(self):
        unsafe = {"query": "Comitê Zeta https://evil.example instruções", "source_group": "any"}
        operations, _ = _research_scope_plan(TEXT, [unsafe, unsafe, FIRST], [TEXT])
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["query_origin"], "deterministic_original_neutral")
        self.assertTrue(all("https://" not in item["query"] for item in operations))
        operations, _ = _research_scope_plan(TEXT, [FIRST, SECOND, {**FIRST, "source_group": "editorial"}], [])
        self.assertEqual(len(operations), 2)
        previous = [_research_query_text(FIRST["query"], "primary"), _research_query_text(SECOND["query"], "editorial")]
        operations, audit = _research_scope_plan(TEXT, [FIRST, SECOND], previous)
        self.assertGreaterEqual(audit["skipped_duplicate_query_count"], 2)
        self.assertLessEqual(len(operations), 2)
        self.assertFalse(any(_research_query_text(item["query"], item["source_group"]) in previous for item in operations))


class ResearchScopePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_retrieval(self, *, planned=None, failure=None, sufficient=False, limit="3"):
        planned = [FIRST, SECOND] if planned is None else planned
        attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}
        requested = {"queries": planned, "leads": [], "coverage": {"status": "success", "planned_query_count": len(planned)}}
        calls = []
        async def search(query):
            calls.append(query)
            if failure and len(calls) == (int(limit) + 1):
                return NewsSearch(status=failure)
            # A plausible search snippet still has no fetched article body.
            return NewsSearch([{"link": "https://www.bbc.com/related", "title": "Resultado confirmado",
                               "snippet": "A afirmação é verdadeira."}])
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": limit}), \
             patch("app.core.pipeline.research_enabled", return_value=True), \
             patch("app.core.pipeline.plan_source_research", new=AsyncMock(return_value=requested)) as model, \
             patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=search)), \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect, \
             patch("app.core.pipeline.usable_source_families", return_value={"bbc", "reuters"} if sufficient else set()), \
             patch("app.core.pipeline.claims_needing_research", return_value=[] if sufficient else [TEXT]):
            result = await _retrieve_source_attribution(TEXT, [TEXT], None)
        return result, model, collect, calls

    async def test_diversified_execution_audits_requested_and_executed_group_inside_original_caps(self):
        result, model, collect, calls = await self.run_retrieval()
        self.assertEqual(len(calls), 5)
        self.assertNotIn("site:", calls[3])
        self.assertIn("site:reuters.com", calls[4])
        self.assertNotIn("site:bcb.gov.br", calls[4])
        model.assert_awaited_once()
        self.assertTrue(all(call.args[0] == TEXT for call in collect.await_args_list))
        self.assertEqual(collect.await_args.kwargs["max_sources"], 10)
        coverage = result["coverage"]
        self.assertEqual(coverage["max_search_queries"], 5)
        self.assertEqual(coverage["retrieval_deadline_seconds"], 105)
        self.assertEqual(coverage["online_research"]["executed_query_count"], 2)
        self.assertEqual(coverage["online_research"]["scope_diversified_query_executed_count"], 1)
        second = coverage["search_queries"][-1]
        self.assertEqual(second["requested_source_group"], "primary")
        self.assertEqual(second["executed_source_group"], "editorial")
        self.assertEqual(second["scope_change_reason"], "independent_family_gap")
        self.assertEqual(result["_documents"], [])
        self.assertEqual(result["selection_audit"]["eligible_family_count"], 0)
        self.assertNotIn("verdict", result)

    async def test_extra_search_rate_quota_or_error_stops_before_reserved_editorial_call(self):
        for failure in ("rate_limited", "timeout", "error", "not_configured"):
            with self.subTest(failure=failure):
                result, model, _, calls = await self.run_retrieval(failure=failure)
                self.assertEqual(len(calls), 4)
                model.assert_awaited_once()
                audit = result["coverage"]["online_research"]
                self.assertEqual(audit["scope_diversified_query_planned_count"], 1)
                self.assertEqual(audit["scope_diversified_query_executed_count"], 0)
                self.assertEqual(audit["executed_query_count"], 1)

    async def test_sufficient_bodies_skip_research_and_source_groups_are_not_evidence_votes(self):
        result, model, _, calls = await self.run_retrieval(sufficient=True)
        model.assert_not_awaited()
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["_documents"], [])
        self.assertNotIn("verdict", result)

    async def test_single_primary_with_one_base_slot_executes_at_most_three_queries_and_marks_gap_not_ai(self):
        result, model, _, calls = await self.run_retrieval(planned=[FIRST], limit="1")
        self.assertEqual(len(calls), 3)
        model.assert_awaited_once()
        audit = result["coverage"]["online_research"]
        self.assertEqual(audit["executed_query_count"], 1)
        self.assertEqual(audit["deterministic_gap_query_executed_count"], 1)
        entry = result["coverage"]["search_queries"][-1]
        self.assertEqual(entry["query_origin"], "deterministic_original_neutral")
        self.assertEqual(entry["method"], "deterministic_research_gap_recovery")
        self.assertIsNone(entry["requested_source_group"])
        self.assertEqual(entry["executed_source_group"], "editorial")
