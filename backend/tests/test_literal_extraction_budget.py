"""Skip redundant extraction, not factual evidence or source comparison."""
from contextlib import ExitStack
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.core.pipeline import run_pipeline
from app.services.claim_policy import input_claims


class LiteralExtractionBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def run_control(self, text, *, router_available=True, router_key="test-only",
                          router_enabled="true", hints=(), use_ai_extraction=True,
                          use_source_crosscheck=True):
        documents = [{"id": "source-control", "text": "A literal source body."}]
        mocks = {
            "analyze_with_openrouter": AsyncMock(return_value={
                "available": router_available, "status": "success" if router_available else "unavailable",
                "claims": list(hints), "decision_role": "search_hints_only", "free_only": True}),
            "extract_claims_with_ai": AsyncMock(return_value=list(hints)),
            "query_fact_check_api": AsyncMock(return_value=[]),
            "search_news": AsyncMock(return_value=[]),
            "detect_ai_text": AsyncMock(return_value={"ai_probability": None}),
            "_retrieve_source_attribution": AsyncMock(return_value={
                "status": "no_results", "matches": [], "coverage": {}, "_documents": documents}),
            "corroborate_sources": AsyncMock(return_value={
                "version": "source_corroboration_v1", "status": "insufficient_sources",
                "state": "insufficient", "decision_role": "grounded_source_comparison",
                "claims": [], "coverage": {}}),
        }
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "OPENROUTER_API_KEY": router_key, "OPENROUTER_ENABLED": router_enabled,
                "GEMINI_API_KEY": "test-only"}))
            for name, mock in mocks.items():
                stack.enter_context(patch("app.core.pipeline." + name, new=mock))
            result = await run_pipeline(text, use_ai_extraction=use_ai_extraction,
                                        use_source_crosscheck=use_source_crosscheck)
        return result, mocks, documents

    def assert_no_extra_extraction(self, result, mocks, text):
        mocks["analyze_with_openrouter"].assert_not_awaited()
        mocks["extract_claims_with_ai"].assert_not_awaited()
        mocks["query_fact_check_api"].assert_awaited_once_with(text.strip())
        mocks["search_news"].assert_awaited_once_with(text.strip())
        self.assertEqual(result["claims"], [])
        report = result["report"]
        self.assertEqual(report["search_claims"], [])
        self.assertEqual(report["claims"], [text.strip()])
        self.assertEqual(report["veracity_status"], "unverified")
        for provider in ("openrouter", "gemini"):
            coverage = report["provider_coverage"][provider]
            self.assertEqual(coverage["status"], "not_requested")
            self.assertEqual(coverage["reason"], "literal_single_sentence_no_extra_extraction")
            self.assertEqual(coverage["decision_role"], "search_hints_only")
            self.assertFalse(coverage["available"])
        for provider in ("google_fact_check", "serper"):
            plan = report["provider_coverage"][provider]["query_plan"]
            self.assertTrue(plan["whole_text_queried"])
            self.assertEqual(plan["query_methods"], ["whole_literal_input"])
            self.assertEqual(plan["extracted_received_count"], 0)
            self.assertFalse(plan["truncated"])

    async def test_short_literal_preserves_negation_dates_amounts_and_qualifiers(self):
        sentences = (
            "A Dra. Ávila não recebeu R$ 1.500,00 em 14/10/2026, segundo o comunicado.",
            "A taxa não caiu 0,25 ponto percentual e permaneceu em 12,5% em 21/10/2026.",
            "O resultado provisório inclui somente adultos de 30 a 39 anos",
            "The Dr. Vale report did not confirm 1.25 mg on Sept. 26, 2026.",
            "  O Prof. Mateus não confirmou a mudança antes de 21/10/2026.  ",
        )
        for text in sentences:
            with self.subTest(text=text):
                result, mocks, _ = await self.run_control(text, hints=("paráfrase descartada",))
                self.assert_no_extra_extraction(result, mocks, text)

    async def test_exact_500_character_sentence_is_searched_whole(self):
        prefix, suffix = "O comunicado ", " não prevê R$ 1.500,00 em 21/10/2026."
        text = prefix + "x" * (500 - len(prefix) - len(suffix)) + suffix
        self.assertEqual(len(text), 500)
        result, mocks, _ = await self.run_control(text)
        self.assert_no_extra_extraction(result, mocks, text)

    async def test_skip_status_is_explicit_even_without_router_configuration(self):
        for key, enabled in (("", "true"), ("test-only", "false")):
            with self.subTest(key_present=bool(key), enabled=enabled):
                text = "A decisão não mudou a taxa em 21/10/2026."
                result, mocks, _ = await self.run_control(text, router_key=key, router_enabled=enabled)
                self.assert_no_extra_extraction(result, mocks, text)

    async def test_short_input_still_retrieves_sources_and_compares_document_bodies(self):
        text = "O relatório não confirmou a mudança em 21/10/2026."
        result, mocks, documents = await self.run_control(text)
        self.assert_no_extra_extraction(result, mocks, text)
        mocks["_retrieve_source_attribution"].assert_awaited_once_with(
            text, [text], None, use_source_crosscheck=True)
        mocks["corroborate_sources"].assert_awaited_once()
        self.assertEqual(mocks["corroborate_sources"].await_args.args, (text, documents, None))
        self.assertTrue(0 < mocks["corroborate_sources"].await_args.kwargs["timeout_seconds"] <= 420)
        self.assertIn("source_crosscheck", result["report"]["provider_coverage"])

    async def test_multiple_sentences_or_paragraphs_keep_router_extraction(self):
        texts = (
            "A taxa não subiu. O valor permaneceu em 12,5% em 21/10/2026.",
            "A taxa não subiu.\n\nO valor permaneceu em 12,5% em 21/10/2026.",
            "A taxa não subiu\nO valor permaneceu em 12,5% em 21/10/2026.",
        )
        for text in texts:
            with self.subTest(text=text):
                hints = [input_claims(text)[-1]]
                result, mocks, _ = await self.run_control(text, hints=hints)
                mocks["analyze_with_openrouter"].assert_awaited_once_with(text)
                mocks["extract_claims_with_ai"].assert_not_awaited()
                self.assertEqual(result["claims"], hints)
                self.assertEqual(result["report"]["provider_coverage"]["openrouter"]["status"], "success")

    async def test_501_character_sentence_keeps_extraction_without_truncation(self):
        prefix, suffix = "O comunicado ", " não prevê R$ 1.500,00 em 21/10/2026."
        text = prefix + "x" * (501 - len(prefix) - len(suffix)) + suffix
        result, mocks, _ = await self.run_control(text, hints=[text])
        mocks["analyze_with_openrouter"].assert_awaited_once_with(text)
        mocks["extract_claims_with_ai"].assert_not_awaited()
        mocks["query_fact_check_api"].assert_awaited_once_with(text)
        mocks["search_news"].assert_not_awaited()
        self.assertEqual(result["claims"], [text])
        self.assertFalse(result["report"]["provider_coverage"]["serper"]["query_plan"]["truncated"])

    async def test_multiple_sentences_keep_gemini_fallback_and_unconfigured_router_path(self):
        text = "A taxa não subiu. O valor permaneceu em 12,5% em 21/10/2026."
        hints = [input_claims(text)[-1]]
        for key in ("test-only", ""):
            with self.subTest(key_present=bool(key)):
                result, mocks, _ = await self.run_control(
                    text, router_available=False, router_key=key, hints=hints)
                self.assertEqual(mocks["analyze_with_openrouter"].await_count, int(bool(key)))
                mocks["extract_claims_with_ai"].assert_awaited_once_with(text)
                self.assertEqual(result["claims"], hints)
                self.assertEqual(result["report"]["provider_coverage"]["gemini"]["status"], "success")

    async def test_explicit_extraction_opt_out_preserves_existing_coverage_and_crosscheck_option(self):
        for text in ("A taxa não subiu.", "A taxa não subiu. O valor permaneceu em 12,5%."):
            with self.subTest(text=text):
                result, mocks, _ = await self.run_control(
                    text, use_ai_extraction=False, use_source_crosscheck=False)
                mocks["analyze_with_openrouter"].assert_not_awaited()
                mocks["extract_claims_with_ai"].assert_not_awaited()
                mocks["corroborate_sources"].assert_not_awaited()
                self.assertEqual(result["claims"], [])
                coverage = result["report"]["provider_coverage"]
                self.assertNotIn("openrouter", coverage)
                self.assertNotIn("gemini", coverage)
                self.assertNotIn("source_crosscheck", coverage)


if __name__ == "__main__":
    unittest.main()
