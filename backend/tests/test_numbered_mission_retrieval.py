"""Offline reading/extraction controls; no historical answers or source votes."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.launch_relations import launch_lead_identity_priority
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import (
    _article_parts, _retrieval_priority, _source_statements, collect_source_attribution,
)
from app.core.pipeline import _source_recovery_queries


CLAIM = "A missão Aurora IX foi lançada em 11 de maio de 2001."


class NumberedMissionReadingTests(unittest.IsolatedAsyncioTestCase):
    def test_launch_editorial_search_is_bilingual_not_restricted_to_school_explainers(self):
        original = CLAIM
        plan = _source_recovery_queries(CLAIM, 3)
        self.assertEqual(len(plan), 2)
        for query, _ in plan:
            self.assertIn('"Aurora IX"', query)
            self.assertNotIn("2001", query)
            self.assertLessEqual(len(query), 500)
        for word in ("lançamento", "launch", "site:bbc.com", "site:reuters.com", "site:apnews.com", "site:ebc.com.br"):
            self.assertIn(word, plan[1][0])
        self.assertNotIn("site:nasa.gov", plan[1][0])
        self.assertEqual(plan[1][1], "literal_identity_event_editorial_sources")
        self.assertEqual(CLAIM, original)
        self.assertEqual(len(_source_recovery_queries(CLAIM, 2)), 1)

    def test_birth_death_and_ambiguous_events_keep_existing_discovery_scope(self):
        for text in ("Aurora IX nasceu em 11 de maio de 2001.", "Aurora IX morreu em 11 de maio de 2001."):
            self.assertEqual(_source_recovery_queries(text, 3)[1][1], "literal_identity_event_editorial_explainers")
        text = "Aurora IX foi lançada e morreu em 11 de maio de 2001."
        self.assertEqual(_source_recovery_queries(text, 3)[0][1], "literal_topic_anchors_primary_sources")

    def test_exact_identity_precedes_different_mission_even_if_year_differs(self):
        exact = _retrieval_priority(CLAIM, "Aurora 9 mission launch 2002", "https://www.nasa.gov/mission/aurora-9/")
        unknown = _retrieval_priority(CLAIM, "Aurora program 2001", "https://www.nasa.gov/program/aurora/")
        different = _retrieval_priority(CLAIM, "Aurora X mission launch 2001", "https://www.nasa.gov/mission/aurora-x/")
        self.assertLess(exact, unknown)
        self.assertLess(unknown, different)

    def test_roman_arabic_paths_multiple_names_and_word_boundaries(self):
        for lead in ("Aurora IX", "aurora-9", "NASA Aurora IX launch", "Aurora X and Aurora IX"):
            with self.subTest(lead=lead):
                self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 0)
        for lead in ("Aurora X", "aurora-10", "Aurora 99"):
            self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 2)
        for lead in ("Aurora IXa", "SuperAurora IX", "Aurora launch", "Aurora IIII", "Aurora 2001"):
            self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 1)
        name = CLAIM.replace("Aurora", "Lunar Aurora")
        self.assertEqual(launch_lead_identity_priority(name, "lunar-aurora-9"), 0)
        self.assertEqual(launch_lead_identity_priority(name, "aurora-9"), 1)

    def test_ambiguous_or_non_launch_claims_keep_existing_priority(self):
        for claim in (CLAIM + " A missão Aurora X também decolou.",
                      CLAIM.replace("foi lançada", "será lançada"),
                      CLAIM.replace("IX", "IIII"),
                      "O Instituto Aurora IX registrou crescimento em 2001.",
                      "O foguete Saturn V lançou a espaçonave Aurora IX em 11 de maio de 2001."):
            self.assertEqual(launch_lead_identity_priority(claim, "Aurora X"), 0)

    async def test_identity_ranking_still_requires_body_and_spends_same_budget(self):
        urls = ["https://www.nasa.gov/mission/aurora-x/", "https://www.nasa.gov/mission/aurora-ix/"]
        unrelated = "Outra notícia não comprova a alegação apresentada."
        async def fetch(url):
            return {"url": url, "sentences": [unrelated], "sentence_roles": ["body"], "truncated": False}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {"link": urls[0], "title": "Aurora X launch 2001"},
                {"link": urls[1], "title": "Aurora IX launch 2002"}], include_documents=True, max_sources=1)
        self.assertEqual([call.args[0] for call in request.await_args_list], [urls[1]])
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)

    def test_clock_zone_date_remains_one_literal_source_statement(self):
        for clock in ("1:47 a.m. EST", "12:40 p.m. PST", "09:08 A.M. UTC"):
            statement = f"The Aurora IX mission launched at {clock} on May 11, 2002."
            self.assertEqual(_source_statements(statement), [statement])
            page = FetchedResource(f"<article><p>{statement}</p></article>".encode(),
                                   "text/html", "https://www.nasa.gov/control/", "utf-8")
            sentences, _, _, roles = _article_parts(page)
            self.assertEqual(sentences, [statement])
            self.assertEqual(roles, ["body"])

    def test_clock_final_period_does_not_swallow_unrelated_sentence(self):
        text = "The Aurora IX mission launched at 1:47 a.m. Another mission arrived in 2002."
        parts = _source_statements(text)
        self.assertEqual(parts, ["The Aurora IX mission launched at 1:47 a.m.", "Another mission arrived in 2002."])
        self.assertEqual(" ".join(parts), text)

    def test_clock_caption_and_publication_do_not_become_body_or_merge(self):
        statement = "The Aurora IX mission launched at 1:47 a.m. EST on May 11, 2002."
        for wrapped in (f"<figcaption>{statement}</figcaption>", f"<h2>{statement}</h2>"):
            page = FetchedResource(f"<article>{wrapped}<p>A different mission launched.</p></article>".encode(),
                                   "text/html", "https://www.nasa.gov/control/", "utf-8")
            sentences, _, _, roles = _article_parts(page)
            self.assertEqual(sentences, [statement, "A different mission launched."])
            self.assertEqual(roles, ["context", "body"])


if __name__ == "__main__":
    unittest.main()
