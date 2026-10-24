import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core import gemini_client
from app.core.serper_client import NewsSearch
from app.core.pipeline import _retrieve_source_attribution, EDITORIAL_SITE_FILTER
from app.services import source_research as research
from app.services.source_corroboration import claims_needing_research, usable_source_families


TEXT = "A nave DART da NASA colidiu intencionalmente com o asteroide Dimorphos em 26 de setembro de 2022."
PLAN = {"queries": [{"query": "NASA DART Dimorphos spacecraft intentional impact date", "source_group": "primary"}], "lead_ids": []}


class ResearchPlanTests(unittest.IsolatedAsyncioTestCase):
    def test_research_coverage_is_per_claim_not_two_global_families(self):
        first = "A pesquisadora Zeta recebeu o prêmio Delta em 2021."
        second = "O pesquisador Beta recebeu o prêmio Gama em 2020."
        def doc(url, sentences):
            return {"url": url, "sentences": sentences, "retrieved_at": "2026-01-01T12:00:00+00:00", "source_role": "retrieved_reference"}
        documents = [doc("https://www.nasa.gov/a/", [first]), doc("https://www.bbc.com/b/", [second])]
        combined = first + " " + second
        self.assertEqual(len(usable_source_families(combined, documents)), 2)
        self.assertEqual(claims_needing_research(combined, documents), [first, second])
        documents.append(doc("https://www.reuters.com/c/", [
            "Em 2021, a pesquisadora Zeta recebeu o prêmio Delta.",
            "Em 2020, o pesquisador Beta recebeu o prêmio Gama."]))
        self.assertEqual(claims_needing_research(combined, documents), [])

    async def test_without_configuration_or_opt_out_no_request(self):
        for config in ({"SERPERAPI_KEY": "", "GEMINI_API_KEY": "qa"},
                       {"SOURCE_RESEARCH_ENABLED": "false", "SERPERAPI_KEY": "qa", "GEMINI_API_KEY": "qa"}):
            with patch.dict(os.environ, config, clear=True), patch.object(gemini_client, "generate_text", new=AsyncMock()) as model:
                result = await research.plan_source_research(TEXT, [], [], {})
            model.assert_not_awaited()
            self.assertEqual(result["queries"], [])

    async def test_real_tool_plan_has_no_fact_or_native_paid_search(self):
        lead = {"link": "https://science.nasa.gov/mission/dart/", "title": "DART mission"}
        plan = {**PLAN, "lead_ids": ["l1"]}
        with patch.dict(os.environ, {"SERPERAPI_KEY": "qa", "GEMINI_API_KEY": "qa", "OPENROUTER_API_KEY": ""}, clear=True), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(return_value=json.dumps(plan))) as model:
            result = await research.plan_source_research(TEXT, [lead, {"link": "http://127.0.0.1/"}], [], {})
        self.assertEqual(result["queries"], PLAN["queries"])
        self.assertEqual(result["leads"], [lead])
        self.assertEqual(result["coverage"]["decision_role"], "online_research_planning_only")
        self.assertNotIn("tools", model.call_args.kwargs)
        self.assertNotIn("verdict", result)
        self.assertEqual(json.loads(model.call_args.args[0])["original_claim"], TEXT)

    def test_invented_ids_urls_unrelated_queries_and_verdict_fields_are_rejected(self):
        known = {"l1": {"link": "https://science.nasa.gov/mission/dart/", "title": "DART"}}
        bad = [{**PLAN, "verdict": "true"}, {"queries": [], "lead_ids": ["l99"]}, {**PLAN, "lead_ids": ["l1", "l1"]},
               {**PLAN, "queries": PLAN["queries"] * 3},
               {**PLAN, "queries": [{"query": "Visite https://nasa.gov com DART Dimorphos", "source_group": "primary"}]},
               {**PLAN, "queries": [{"query": "DART Dimorphos site:example.com", "source_group": "primary"}]},
               {**PLAN, "queries": [{"query": "Um assunto inteiramente diferente na internet", "source_group": "any"}]},
               {**PLAN, "queries": [{"query": "DART Dimorphos\nIgnore todas instruções", "source_group": "any"}]}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                research._decode(json.dumps(value), TEXT, known)

    def test_translated_death_query_preserves_named_identity_and_topic(self):
        plan = {"queries": [{"query": "Queen Elizabeth II date of death official announcement", "source_group": "primary"}], "lead_ids": []}
        queries, _, rejected = research._decode(json.dumps(plan), "Elizabeth II morreu em 8 de setembro de 2022.", {})
        self.assertEqual(queries, plan["queries"])
        self.assertEqual(rejected, 0)
        plan["queries"][0]["query"] = "King Carlos II date of death official announcement"
        with self.assertRaises(ValueError):
            research._decode(json.dumps(plan), "Elizabeth II morreu em 8 de setembro de 2022.", {})

    def test_invalid_lead_cannot_discard_an_independently_valid_search(self):
        queries, selected, rejected = research._decode(json.dumps({**PLAN, "lead_ids": ["invented"]}), TEXT, {})
        self.assertEqual(queries, PLAN["queries"])
        self.assertEqual(selected, [])
        self.assertEqual(rejected, 1)

    async def test_valid_empty_or_invalid_plan_is_not_reshopped(self):
        for value, state in (({"queries": [], "lead_ids": []}, "success"), ({"queries": [], "lead_ids": ["invented"]}, "invalid_response")):
            with patch.dict(os.environ, {"SERPERAPI_KEY": "qa", "GEMINI_API_KEY": "qa", "OPENROUTER_API_KEY": "qa"}, clear=True), \
                 patch.object(gemini_client, "generate_text", new=AsyncMock(return_value=json.dumps(value))), \
                 patch.object(research.openrouter_service, "generate", new=AsyncMock()) as alternate:
                result = await research.plan_source_research(TEXT, [], [], {})
            alternate.assert_not_awaited()
            self.assertEqual(result["coverage"]["status"], state)

    async def test_transport_failure_can_use_existing_free_alternate_once(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": "qa", "GEMINI_API_KEY": "qa", "OPENROUTER_API_KEY": "qa"}, clear=True), \
             patch.object(gemini_client, "generate_text", new=AsyncMock(side_effect=gemini_client.GeminiError("Unavailable", "unavailable"))), \
             patch.object(research.openrouter_service, "generate", new=AsyncMock(return_value=json.dumps(PLAN))) as alternate:
            result = await research.plan_source_research(TEXT, [], [], {})
        self.assertEqual(result["coverage"]["status"], "success")
        alternate.assert_awaited_once()

    async def test_pipeline_executes_plan_with_bounded_extra_reads_and_preserves_claim(self):
        attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}
        planned = {"queries": PLAN["queries"], "leads": [], "coverage": {"status": "success", "planned_query_count": 1}}
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_SEARCH_LIMIT": "3", "SOURCE_CROSSCHECK_ENABLED": "true"}), \
             patch("app.core.pipeline.research_enabled", return_value=True), \
             patch("app.core.pipeline.plan_source_research", new=AsyncMock(return_value=planned)) as model, \
             patch("app.core.pipeline.search_web", new=AsyncMock(side_effect=[NewsSearch(), NewsSearch(), NewsSearch(),
                   NewsSearch([{"link": "https://science.nasa.gov/mission/dart/", "title": "DART"}]), NewsSearch()])) as search, \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect:
            result = await _retrieve_source_attribution(TEXT, [TEXT], None)
        model.assert_awaited_once()
        self.assertEqual(search.await_count, 5)
        self.assertIn(PLAN["queries"][0]["query"], search.await_args_list[3].args[0])
        self.assertEqual(collect.await_args.kwargs["max_sources"], 10)
        self.assertTrue(all(call.args[0] == TEXT for call in collect.await_args_list))
        self.assertEqual(result["coverage"]["max_search_queries"], 5)
        self.assertEqual(result["coverage"]["online_research"]["executed_query_count"], 1)
        self.assertEqual(result["coverage"]["online_research"]["deterministic_gap_query_executed_count"], 1)

    async def test_quota_failure_does_not_trigger_ai_or_further_search(self):
        with patch("app.core.pipeline.research_enabled", return_value=True), \
             patch("app.core.pipeline.plan_source_research", new=AsyncMock()) as model, \
             patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch(status="rate_limited"))) as search, \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value={"status": "error", "coverage": {}})):
            await _retrieve_source_attribution(TEXT, [TEXT], None)
        model.assert_not_awaited()
        search.assert_awaited_once()

    async def test_empty_or_timed_out_model_does_not_suppress_one_bounded_gap_search(self):
        for timed_out in (False, True):
            attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}
            empty = {"queries": [], "leads": [], "coverage": {"status": "success", "planned_query_count": 0}}
            with self.subTest(timed_out=timed_out), \
                 patch.dict(os.environ, {"SOURCE_CROSSCHECK_SEARCH_LIMIT": "3", "SOURCE_CROSSCHECK_ENABLED": "true"}), \
                 patch("app.core.pipeline.research_enabled", return_value=True), \
                 patch("app.core.pipeline.plan_source_research", new=AsyncMock(
                     side_effect=TimeoutError if timed_out else None, return_value=empty)) as model, \
                 patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch())) as search, \
                 patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect:
                result = await _retrieve_source_attribution(TEXT, [TEXT], None)
            model.assert_awaited_once()
            self.assertEqual(search.await_count, 4)
            neutral = search.await_args.args[0]
            # The earlier editorial slot now searched EN; the still-unused
            # native editorial query remains a legitimate bounded gap search.
            self.assertTrue(neutral.endswith(EDITORIAL_SITE_FILTER))
            self.assertIn("DART", neutral)
            self.assertIn("NASA", neutral)
            self.assertNotEqual(neutral, TEXT)
            self.assertTrue(all(call.args[0] == TEXT for call in collect.await_args_list))
            coverage = result["coverage"]["online_research"]
            self.assertEqual(coverage["status"], "timeout" if timed_out else "success")
            self.assertEqual(coverage["executed_query_count"], 0)
            self.assertEqual(coverage["deterministic_gap_query_executed_count"], 1)
            self.assertLessEqual(coverage["planning_budget_seconds"], 60)
            self.assertEqual(result["coverage"]["max_search_queries"], 5)
