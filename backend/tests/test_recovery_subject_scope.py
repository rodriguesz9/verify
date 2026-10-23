"""Discovery controls, never source/factual votes."""
import unittest
from unittest.mock import AsyncMock, patch

from app.core.pipeline import _source_recovery_queries, _research_query_text, _research_scope_plan
from app.services.source_attribution import _retrieval_priority, collect_source_attribution


class RecoverySubjectScopeTests(unittest.IsolatedAsyncioTestCase):
    def test_unknown_subject_remains_open_and_planner_cannot_invent_institution(self):
        text = "A pesquisadora Zeta recebeu o prêmio de química em 2002."
        self.assertNotIn("site:", _source_recovery_queries(text, 3)[0][0])
        self.assertEqual(_research_query_text("NASA prêmio química pesquisa em 2002", "primary", text),
                         "NASA prêmio química pesquisa em 2002")
        original = "A NASA informou o resultado da missão em 2002."
        self.assertIn("site:nasa.gov", _research_query_text("missão resultado pesquisa em 2002", "primary", original))
        operations, _ = _research_scope_plan(text, [{"query": "NASA prêmio química pesquisa em 2002", "source_group": "primary"}], [])
        self.assertEqual(len(operations), 2)
        self.assertNotIn("site:", _research_query_text(operations[0]["query"], "primary", text))

    def test_unrelated_same_year_does_not_outrank_named_subject_other_year(self):
        text = "O projeto Zeta Omega começou em 2002."
        relevant = _retrieval_priority(text, "Projeto Zeta Omega começou em 2001", "https://www.bbc.com/zeta-omega-2001")
        unrelated = _retrieval_priority(text, "Atlas escolar estatístico 2002", "https://www.ibge.gov.br/atlas-2002")
        self.assertLess(relevant, unrelated)

    async def test_family_diversity_does_not_promote_unrelated_blank_lead(self):
        text = "O projeto Zeta Omega começou em 2002."
        leads = [{"link": "https://www.bbc.com/zeta-one", "title": "Projeto Zeta Omega começou em 2002"},
                 {"link": "https://www.bbc.com/zeta-two", "title": "Projeto Zeta Omega histórico de 2002"},
                 {"link": "https://www.ibge.gov.br/atlas-2002", "title": "Atlas escolar estatístico 2002"}]
        with patch("app.services.source_attribution._fetch_article", new=AsyncMock(return_value={"failure": "error"})) as fetch:
            result = await collect_source_attribution(text, [text], search_results=leads, include_documents=True, max_sources=2)
        self.assertEqual([call.args[0] for call in fetch.await_args_list], [item["link"] for item in leads[:2]])
        self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 2)
        self.assertEqual(result["matches"], [])
