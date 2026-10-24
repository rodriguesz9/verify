"""Bilingual lead ranking only: no source fact or benchmark answer supplied."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_attribution import _retrieval_priority, collect_source_attribution
from app.services.source_queries import discovery_topic_tokens


CLAIM = "Em 10 de abril de 2001, a Organização Mundial da Saúde caracterizou Zeta-31 como uma pandemia."


class BilingualDiscoveryPriorityTests(unittest.IsolatedAsyncioTestCase):
    def test_existing_aliases_rank_event_article_ahead_of_same_subject_dashboard(self):
        dashboard = _retrieval_priority(CLAIM, "WHO Zeta-31 cases dashboard", "https://www.who.int/zeta31/cases")
        article = _retrieval_priority(CLAIM, "WHO classified Zeta-31 as pandemic", "https://www.who.int/bulletin")
        self.assertLess(article, dashboard)

    def test_aliases_preserve_unknown_names_and_compound_identity_not_calendar_or_polarity(self):
        tokens = discovery_topic_tokens("A espaçonave Ômega não colidiu com Zeta-31 em abril de 2001.")
        self.assertTrue({"spacecraft", "omega", "event-impact", "zeta-31"} <= tokens)
        self.assertTrue(tokens.isdisjoint({"nao", "abril", "2001", "31", "zeta"}))
        self.assertNotEqual(discovery_topic_tokens("Zeta-31"), discovery_topic_tokens("Zeta-32"))
        self.assertNotIn("who", discovery_topic_tokens("Organização Mundial do Comércio"))
        self.assertEqual(discovery_topic_tokens(None), set())

    def test_known_translation_never_suppresses_unknown_named_subject(self):
        claim = "A sonda Ômega colidiu com o asteroide Zeta em 2001."
        matching = _retrieval_priority(claim, "Omega spacecraft collided with Zeta asteroid 2001", "https://www.bbc.com/matching")
        unrelated = _retrieval_priority(claim, "Theta spacecraft collided with Delta asteroid 2001", "https://www.bbc.com/unrelated")
        self.assertLess(matching, unrelated)

    def test_slug_is_not_one_token_but_numbered_identity_is_preserved(self):
        slug = discovery_topic_tokens("/news/who-classified-zeta-31-as-pandemic/2001-2002/")
        self.assertTrue({"who", "event-classification", "zeta-31", "pandemic"} <= slug)
        self.assertTrue(slug.isdisjoint({"zeta", "31", "2001", "2002", "2001-2002", "as"}))
        matching = _retrieval_priority(CLAIM, "", "https://www.who.int/who-classified-zeta-31-as-pandemic")
        unrelated = _retrieval_priority(CLAIM, "", "https://www.who.int/who-theta-32-cases-dashboard")
        self.assertLess(matching, unrelated)

    def test_numbered_name_does_not_turn_into_unnumbered_topic(self):
        tokens = discovery_topic_tokens("Zeta-31a colidiu com Delta-52 em 2001-2002.")
        self.assertTrue({"zeta-31a", "delta-52", "event-impact"} <= tokens)
        self.assertTrue(tokens.isdisjoint({"zeta", "delta", "31", "52", "2001-2002"}))
        self.assertNotEqual(tokens, discovery_topic_tokens("Zeta-31b colidiu com Delta-52 em 2001-2002."))

    async def test_one_read_chooses_translated_article_but_title_does_not_supply_body_evidence(self):
        dashboard, article = "https://www.who.int/zeta31/cases", "https://www.who.int/bulletin"
        unrelated_body = {"url": article, "title": "WHO classified Zeta-31 as pandemic", "truncated": False,
                          "sentences": ["This document contains no corresponding complete event statement."],
                          "sentence_roles": ["body"]}
        cache = {}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(return_value=unrelated_body)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {"link": dashboard, "title": "WHO Zeta-31 cases dashboard"},
                {"link": article, "title": "WHO classified Zeta-31 as pandemic"}],
                include_documents=True, max_sources=1, fetched_cache=cache)
        fetch.assert_awaited_once_with(article)
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)
        self.assertEqual(result["matches"], [])
        self.assertEqual(CLAIM, "Em 10 de abril de 2001, a Organização Mundial da Saúde caracterizou Zeta-31 como uma pandemia.")


if __name__ == "__main__":
    unittest.main()
