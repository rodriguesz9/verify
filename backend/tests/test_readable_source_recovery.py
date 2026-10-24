"""Current reader capabilities guide discovery, never MIME or truth judgments."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services import source_attribution as attribution, source_research as research
from app.services.source_readability import known_unsupported_lead, reader_capabilities


CLAIM = "A pesquisadora Zeta morreu em 12 de agosto de 2021."
PDF = "https://www.nasa.gov/records/zeta.pdf"
HTML1 = "https://www.bbc.com/news/zeta"
HTML2 = "https://www.reuters.com/world/zeta"


def body(url):
    return {"url": url, "title": "Controle sintético", "sentences": [CLAIM],
            "sentence_roles": ["body"], "truncated": False, "reference_leads": [],
            "retrieved_at": "2026-10-18T12:00:00+00:00"}


class ReadabilityHintTests(unittest.TestCase):
    def test_suffix_hint_is_path_only_casefolded_and_decoded(self):
        for url in (PDF, PDF.upper(), "https://www.nasa.gov/report.%70%64%66",
                    "https://www.nasa.gov/report.docx?download=1"):
            self.assertTrue(known_unsupported_lead(url))
        for url in (HTML1, HTML1 + "?source=report.pdf", HTML1 + "#report.pdf",
                    "https://www.nasa.gov/report", "https://www.nasa.gov/pdf/overview.html",
                    "https://www.nasa.gov/topic.pdf/", None, {}):
            self.assertFalse(known_unsupported_lead(url))

    def test_capability_contract_matches_actual_reader_mime_allowlist(self):
        caps = reader_capabilities()
        self.assertEqual(set(caps["content_types"]), attribution._ALLOWED_TYPES)
        self.assertNotIn("application/pdf", caps["content_types"])
        self.assertFalse(caps["executes_javascript"])
        self.assertFalse(caps["extracts_pdf_text"])
        self.assertTrue(caps["url_suffix_is_only_a_discovery_hint"])

    def test_model_lead_ids_cannot_select_known_unreadable_files(self):
        known = research._lead_map([{"link": PDF, "title": "Zeta primary record"},
            {"link": HTML1, "title": "Zeta retrospective"}], None)
        self.assertEqual(known, {"l1": {"link": HTML1, "title": "Zeta retrospective"}})
        with self.assertRaises(ValueError):
            research._decode(json.dumps({"queries": [], "lead_ids": ["invented-pdf-id"]}), CLAIM, known)


class ReadableRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_readable_bodies_precede_even_cited_pdf_inside_same_attempt_cap(self):
        leads = [{"link": PDF, "title": "Zeta original", "retrieval_method": "ai_selected_candidate_reference"},
                 {"link": HTML1, "title": CLAIM}, {"link": HTML2, "title": CLAIM}]
        with patch.object(attribution, "_fetch_article", new=AsyncMock(
                side_effect=lambda url: body(url))) as fetch:
            result = await attribution.collect_source_attribution(
                CLAIM, [CLAIM], search_results=leads, include_documents=True, max_sources=2, fetched_cache={})
        self.assertEqual({call.args[0] for call in fetch.await_args_list}, {HTML1, HTML2})
        self.assertEqual(result["coverage"]["new_fetch_count"], 2)
        self.assertEqual(result["coverage"]["known_unsupported_lead_count"], 1)
        self.assertEqual(result["coverage"]["known_unsupported_selected_count"], 0)
        self.assertEqual({d["url"] for d in result["_documents"]}, {HTML1, HTML2})
        self.assertNotIn("veracity_status", result)

    async def test_prior_pdf_failure_still_spends_budget_and_is_not_retried(self):
        cache = {PDF: {"failure": "unsupported_content"}}
        leads = [{"link": PDF, "title": CLAIM}, {"link": HTML1, "title": CLAIM}, {"link": HTML2, "title": CLAIM}]
        with patch.object(attribution, "_fetch_article", new=AsyncMock(
                side_effect=lambda url: body(url))) as fetch:
            result = await attribution.collect_source_attribution(
                CLAIM, [CLAIM], search_results=leads, include_documents=True, max_sources=2, fetched_cache=cache)
        fetch.assert_awaited_once()
        self.assertNotEqual(fetch.await_args.args[0], PDF)
        self.assertEqual(len(cache), 2)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["coverage"]["fetch_failure_counts"]["unsupported_content"], 1)

    async def test_submitted_url_is_not_silently_replaced_by_discovery_preferences(self):
        with patch.object(attribution, "_fetch_article", new=AsyncMock(
                return_value={"failure": "unsupported_content"})) as fetch:
            result = await attribution.collect_source_attribution(
                CLAIM, [CLAIM], source_url=PDF, search_results=[{"link": HTML1}],
                include_documents=True, max_sources=1, fetched_cache={})
        fetch.assert_awaited_once_with(PDF)
        self.assertEqual(result["coverage"]["fetch_failure_counts"]["unsupported_content"], 1)
        self.assertEqual(result["_documents"], [])

    async def test_hint_does_not_permanently_block_pdf_shaped_url_returning_real_html(self):
        with patch.object(attribution, "_fetch_article", new=AsyncMock(return_value=body(PDF))) as fetch:
            result = await attribution.collect_source_attribution(
                CLAIM, [CLAIM], search_results=[{"link": PDF}], include_documents=True, fetched_cache={})
        fetch.assert_awaited_once_with(PDF)
        self.assertEqual(result["coverage"]["known_unsupported_selected_count"], 1)
        self.assertEqual(result["_documents"][0]["url"], PDF)

    async def test_mime_rejection_still_applies_to_extensionless_urls(self):
        from app.services.public_fetch import FetchedResource
        fake_pdf = FetchedResource(b"%PDF-invalid", "application/pdf", HTML1, None)
        with patch.object(attribution, "fetch_public_resource", new=AsyncMock(return_value=fake_pdf)):
            self.assertEqual(await attribution._fetch_article(HTML1), {"failure": "unsupported_content"})

    async def test_planner_receives_real_tool_limits_without_pdf_ids_or_guessed_truth(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": "offline", "GEMINI_API_KEY": "offline",
                "SOURCE_RESEARCH_ENABLED": "true", "OPENROUTER_API_KEY": ""}, clear=True), \
             patch.object(research.gemini_client, "generate_text", new=AsyncMock(
                 return_value=json.dumps({"queries": [], "lead_ids": ["l1"]}))) as generate:
            result = await research.plan_source_research(
                CLAIM, [{"link": PDF}, {"link": HTML1}], [], {})
        sent = json.loads(generate.await_args.args[0])
        self.assertEqual(sent["original_claim"], CLAIM)
        self.assertEqual(sent["reader_capabilities"], reader_capabilities())
        self.assertEqual([lead["link"] for lead in sent["candidate_leads"]], [HTML1])
        self.assertIn("sem JavaScript nem extração de PDF", generate.await_args.kwargs["system_instruction"])
        self.assertEqual(result["leads"], [{"link": HTML1, "title": ""}])
        self.assertNotIn("verdict", result)
        self.assertNotIn("tools", generate.await_args.kwargs)
