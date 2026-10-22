"""Discovery language controls: a locale/search result never becomes proof."""
import os
import unittest
from unittest.mock import AsyncMock, patch
import httpx

from app.core.pipeline import _source_recovery_queries, _retrieve_source_attribution
from app.core.serper_client import NewsSearch, search_web
from app.services.source_queries import editorial_source_query, neutral_source_query

TEXT = "Em 12 de agosto de 2021, a nave Aurora da NASA colidiu intencionalmente com o asteroide Zeta."


class BilingualEditorialQueriesTests(unittest.TestCase):
    def test_named_foreign_institution_uses_only_known_vocabulary_not_new_facts(self):
        original = TEXT
        query, language = editorial_source_query(TEXT)
        self.assertEqual(language, "en")
        for token in ("Aurora", "NASA", "Zeta", "spacecraft", "intentional", "asteroid", "2021"):
            self.assertIn(token, query.split())
        for token in ("12", "agosto", "verdadeira", "false", "2022"):
            self.assertNotIn(token, query.split())
        self.assertEqual(TEXT, original)

    def test_domestic_mixed_unknown_and_untranslated_topics_keep_native_query(self):
        for text in (
            "O IBGE informou que o PIB brasileiro cresceu em 2021.",
            "O Copom e a NASA discutiram crescimento em 2021.",
            "O Instituto Aurora informou a temperatura média em 2021.",
            "A NASA registrou o fenômeno inédito Aurora em 2021.",
        ):
            with self.subTest(text=text):
                self.assertEqual(editorial_source_query(text), (neutral_source_query(text, preserve_period=True), "pt-br"))

    def test_recovery_keeps_two_slots_and_filters_are_not_source_votes(self):
        plan = _source_recovery_queries(TEXT, 3)
        self.assertEqual(len(plan), 2)
        self.assertIn("site:nasa.gov", plan[0][0])
        self.assertNotIn("site:nasa.gov", plan[1][0])
        self.assertIn("site:bbc.com", plan[1][0])
        self.assertEqual(plan[1][1], "literal_topic_anchors_bilingual_editorial_sources")
        self.assertIn("intentional", plan[1][0])
        self.assertEqual(len(_source_recovery_queries(TEXT, 2)), 1)


class BilingualEditorialTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_explicit_english_profile_changes_locale_in_one_existing_send(self):
        for kwargs, expected in (({}, {"gl": "br", "hl": "pt-br"}),
                                 ({"language": "en"}, {"gl": "us", "hl": "en"})):
            with self.subTest(kwargs=kwargs), patch.dict(os.environ, {"SERPERAPI_KEY": "unit-test-not-secret"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200,
                     json={"organic": [{"link": "https://www.bbc.com/public-report", "title": "Report"}]}))) as post:
                result = await search_web(TEXT, **kwargs)
            post.assert_awaited_once()
            payload = post.await_args.kwargs["json"]
            self.assertEqual({key: payload[key] for key in ("gl", "hl")}, expected)
            self.assertEqual(payload["q"], TEXT)
            self.assertEqual(payload["num"], 10)
            self.assertEqual(result.status, "success")
            self.assertEqual(result, [{"link": "https://www.bbc.com/public-report", "title": "Report"}])

    async def test_invalid_locale_never_sends_or_reads_a_different_endpoint(self):
        for language in ("fr", "en-US", "https://example.test/", "en\n", None, True):
            with self.subTest(language=language), patch("httpx.AsyncClient.post", new=AsyncMock()) as post:
                result = await search_web(TEXT, language=language)
            self.assertEqual(result.status, "invalid_configuration")
            post.assert_not_awaited()

    async def test_quota_has_no_retry_or_locale_fallback(self):
        with patch.dict(os.environ, {"SERPERAPI_KEY": "unit-test-not-secret"}), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(429))) as post:
            result = await search_web(TEXT, language="en")
        self.assertEqual(result.status, "rate_limited")
        post.assert_awaited_once()

    async def test_pipeline_executes_declared_english_slot_without_extra_request_or_claim_change(self):
        attribution = {"status": "no_results", "matches": [], "coverage": {}, "_documents": []}
        with patch.dict(os.environ, {"SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_SEARCH_LIMIT": "3"}), \
             patch("app.core.pipeline.research_enabled", return_value=False), \
             patch("app.core.pipeline.collect_source_attribution", new=AsyncMock(return_value=attribution)) as collect, \
             patch("app.core.pipeline.search_web", new=AsyncMock(return_value=NewsSearch())) as search:
            result = await _retrieve_source_attribution(TEXT, [TEXT], None)
        self.assertEqual(search.await_count, 3)
        self.assertEqual([call.kwargs for call in search.await_args_list], [{}, {}, {"language": "en"}])
        self.assertTrue(all(call.args[0] == TEXT for call in collect.await_args_list))
        self.assertEqual(result["coverage"]["max_search_queries"], 3)
        self.assertEqual(result["coverage"]["search_queries"][-1]["search_language"], "en")
