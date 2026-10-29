"""Paginated-listing discovery hints preserve body guards and read limits."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.source_attribution import _retrieval_priority, collect_source_attribution
from app.services.source_readability import known_paginated_listing_lead, known_unsupported_lead


CLAIM = 'O Instituto Zeta publicou os dados do PIB em 2002.'
BASE = 'https://www.cnnbrasil.com.br'
LISTING = BASE + '/tudo-sobre/instituto-zeta/pagina/18/'
ARTICLE = BASE + '/economia/dados-do-pib-divulgados/'
LISTING_TITLE = 'Instituto Zeta PIB | CNN Brasil'
ARTICLE_TITLE = 'Dados do PIB foram divulgados'


class PaginatedListingPriorityTests(unittest.IsolatedAsyncioTestCase):
    def test_closed_taxonomy_or_archive_pagination_only(self):
        for path in ('/tudo-sobre/instituto-zeta/pagina/18/', '/topics/zeta/page/2',
                     '/tag/zeta/page/3/', '/category/science/page/2/',
                     '/archives/2002/page/4/', '/pt-br/assunto/zeta/página/5/',
                     '/TOPICS/Zeta/PAGE/2/'):
            with self.subTest(path=path):
                self.assertTrue(known_paginated_listing_lead(BASE + path))
                self.assertFalse(known_unsupported_lead(BASE + path))
        for value in (None, 123, 'https://[', BASE + '/news/actual-article/page/2/',
                      BASE + '/economia/dados-do-pib/pagina/18/',
                      BASE + '/topics/zeta/', BASE + '/search?q=zeta&page=2',
                      BASE + '/topics/zeta?page=2', BASE + '/archive-page-2/',
                      BASE + '/topics/zeta/page/2/details', BASE + '/topics/zeta/page/zero/',
                      BASE + '/topics/zeta/page/0/', BASE + '/topics/zeta/page/2.pdf',
                      'https://example.test/' + 'x' * 4100):
            with self.subTest(value=value):
                self.assertFalse(known_paginated_listing_lead(value))

    def test_listing_repetition_does_not_beat_direct_article_after_same_high_priority_bands(self):
        listing = _retrieval_priority(CLAIM, LISTING_TITLE, LISTING)
        article = _retrieval_priority(CLAIM, ARTICLE_TITLE, ARTICLE)
        self.assertEqual(listing[:4], article[:4])
        self.assertLess(article, listing)
        self.assertEqual(listing[4], True)
        self.assertEqual(article[4], False)
        # A real article's second page is not demoted as an archive.
        second_page = _retrieval_priority(CLAIM, ARTICLE_TITLE, ARTICLE + 'page/2/')
        self.assertFalse(second_page[4])

    def test_relevant_topic_and_period_keep_precedence_over_listing_hint(self):
        listing = _retrieval_priority(CLAIM, LISTING_TITLE + ' 2002', LISTING)
        wrong_year = _retrieval_priority(CLAIM, ARTICLE_TITLE + ' 2001', ARTICLE)
        unrelated = _retrieval_priority(CLAIM, 'Projeto Omega recebeu prêmio de química 2002',
                                        BASE + '/ciencia/premio-omega/')
        self.assertLess(listing, wrong_year)
        self.assertLess(listing, unrelated)
        self.assertEqual(listing[2], False)  # Existing period index remains unchanged.
        self.assertEqual(wrong_year[2], True)

    def test_listing_hint_does_not_override_launch_mission_or_completed_phase(self):
        claim = 'A missão Aurora IX foi lançada em 11 de maio de 2001.'
        exact_completed = _retrieval_priority(claim, 'Aurora IX launched May 2002',
                                               BASE + '/topics/aurora-ix/page/2/')
        wrong_completed = _retrieval_priority(claim, 'Aurora X launched May 2002',
                                               BASE + '/science/aurora-x-launched/')
        exact_preview = _retrieval_priority(claim, 'Aurora IX scheduled launch May 2001',
                                             BASE + '/science/aurora-ix-preview/')
        self.assertLess(exact_completed, wrong_completed)
        self.assertLess(exact_completed, exact_preview)

    async def test_same_family_slot_reads_article_first_and_does_not_use_headline_as_evidence(self):
        async def fetch(url):
            return {'url': url, 'title': 'Another subject', 'sentences': ['Outro assunto sem prova da alegação.'],
                    'sentence_roles': ['body'], 'truncated': False}
        cache = {}
        with patch('app.services.source_attribution._fetch_article', new=AsyncMock(side_effect=fetch)) as call:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {'link': LISTING, 'title': LISTING_TITLE},
                {'link': ARTICLE, 'title': ARTICLE_TITLE}], include_documents=True, max_sources=1,
                fetched_cache=cache)
        self.assertEqual([item.args[0] for item in call.await_args_list], [ARTICLE])
        self.assertEqual(result['coverage']['cumulative_fetch_attempt_count'], 1)
        self.assertEqual(result['matches'], [])

    async def test_only_listing_remains_available_and_failure_spends_existing_attempt_without_retry(self):
        cache = {}
        with patch('app.services.source_attribution._fetch_article',
                   new=AsyncMock(return_value={'failure': 'blocked_or_unavailable'})) as call:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {'link': LISTING, 'title': LISTING_TITLE}], include_documents=True,
                max_sources=1, fetched_cache=cache)
            await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {'link': LISTING, 'title': LISTING_TITLE}], include_documents=True,
                max_sources=1, fetched_cache=cache)
        call.assert_awaited_once_with(LISTING)
        self.assertEqual(result['coverage']['cumulative_fetch_attempt_count'], 1)
        self.assertEqual(result['coverage']['fetch_failure_counts']['blocked_or_unavailable'], 1)
        self.assertEqual(result['coverage']['known_unsupported_selected_count'], 0)
        self.assertEqual(result['matches'], [])
