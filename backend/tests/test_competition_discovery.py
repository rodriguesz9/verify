"""Discovery ordering only: no stored champions, live requests or source votes."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.competition_relations import competition_lead_priority
from app.services.source_attribution import _retrieval_priority, collect_source_attribution


CLAIM = "O Zeta venceu a Copa do Mundo de futebol masculino de 2001."


class CompetitionDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def test_event_before_ancillary_official_page(self):
        recap = _retrieval_priority(CLAIM, "Omega venceu a Copa do Mundo de 2001", "https://www.bbc.com/sport/recap")
        coins = _retrieval_priority(CLAIM, "Moedas comemorativas Copa do Mundo 2001", "https://www.bcb.gov.br/moedas/")
        self.assertLess(recap, coins)

    def test_does_not_prefer_the_claimed_team_or_relation(self):
        for team in ("Zeta", "Omega", "Alfa"):
            self.assertEqual(competition_lead_priority(CLAIM, f"{team} venceu a Copa do Mundo 2001"), 0)
        self.assertEqual(competition_lead_priority(CLAIM, "Zeta não venceu a Copa do Mundo 2001"), 0)

    def test_year_category_and_ancillary_pages_rank_below_unknown(self):
        for lead in ("Copa do Mundo 2002 campeão", "Copa do Mundo feminina 2001 campeão",
                     "Copa do Mundo sub-20 2001 campeão", "Copa do Mundo 2001 moedas",
                     "2001 FIFA World Cup commemorative coin", "Copa do Mundo 2001 ingressos",
                     "Copa do Mundo 2001 circular"):
            self.assertEqual(competition_lead_priority(CLAIM, lead), 3)
        self.assertEqual(competition_lead_priority(CLAIM, "Campeões de futebol"), 2)
        self.assertEqual(competition_lead_priority(CLAIM, "Copa do Mundo 2001"), 1)

    def test_slug_and_english_hints_do_not_need_team_names(self):
        self.assertEqual(competition_lead_priority(CLAIM, "/2001-fifa-world-cup-winner/"), 0)
        self.assertEqual(competition_lead_priority(CLAIM, "/copa_do_mundo_2001_campeao/"), 0)

    def test_ambiguous_qualified_and_other_claims_keep_order(self):
        for claim in (CLAIM + " Foi invicto.", CLAIM.replace("venceu", "poderia vencer"),
                      "O PIB aumentou em 2001.", CLAIM.replace("masculino", "feminino")):
            self.assertEqual(competition_lead_priority(claim, "Copa do Mundo 2002 moedas"), 0)

    async def test_ranking_does_not_turn_headline_into_evidence_or_expand_budget(self):
        coins = "https://www.bcb.gov.br/moedas/"
        recap = "https://www.bbc.com/sport/recap"
        async def fetch(url):
            return {"url": url, "sentences": ["Esta página não apresenta o vencedor da competição."],
                    "sentence_roles": ["body"], "truncated": False}
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {"link": coins, "title": "Copa do Mundo 2001 moedas comemorativas"},
                {"link": recap, "title": "Omega venceu a Copa do Mundo 2001"}],
                include_documents=True, max_sources=1)
        self.assertEqual([call.args[0] for call in request.await_args_list], [recap])
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)


if __name__ == "__main__":
    unittest.main()
