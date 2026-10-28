"""Launch discovery order never supplies an event relation or truth label."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.launch_relations import launch_lead_phase_priority, launch_lead_identity_priority, launch_date_relation
from app.services.source_attribution import _retrieval_priority, collect_source_attribution


CLAIM = 'A missão Aurora IX foi lançada em 11 de maio de 2001.'


class LaunchDiscoveryPhaseTests(unittest.IsolatedAsyncioTestCase):
    def rank(self, title, path, claim=CLAIM):
        return _retrieval_priority(claim, title, 'https://www.bbc.com/' + path)

    def test_completed_mission_report_precedes_preview_even_when_claimed_year_matches_preview(self):
        completed = self.rank('Aurora 9 launched on May 11, 2002', '2002/05/11/aurora-9-launch/')
        preview = self.rank('Aurora IX prepara lançamento em maio de 2001', '2001/05/aurora-ix-launch/')
        platform = self.rank('Aurora IX chega à plataforma de lançamento', 'aurora-ix-launch-pad/')
        hub = self.rank('Aurora IX mission overview', 'mission/aurora-ix/')
        self.assertLess(completed, hub)
        self.assertLess(hub, platform)
        self.assertLess(completed, preview)

    def test_phase_is_generic_for_program_number_and_does_not_choose_an_agreeable_year(self):
        for program, number in (('Aurora', 'IX'), ('Zeta', 'III'), ('Lunar Delta', '7')):
            claim = f'A missão {program} {number} foi lançada em 11 de maio de 2001.'
            for year in (2000, 2001, 2002):
                with self.subTest(program=program, year=year):
                    self.assertEqual(launch_lead_phase_priority(claim, f'{program} {number} launched in {year}'), 0)

    def test_wrong_mission_never_outranks_matching_mission_by_completed_language(self):
        exact_preview = self.rank('Aurora IX scheduled launch 2001', 'aurora-ix-launch/')
        unknown = self.rank('Aurora program launches in 2001', 'aurora-program/')
        other = self.rank('Aurora X launched in 2001', 'aurora-x-launch/')
        self.assertLess(exact_preview, unknown)
        self.assertLess(unknown, other)

    def test_short_explicit_mission_keeps_identity_and_phase_ahead_of_generic_topics(self):
        claim = 'A missão Io II foi lançada em 11 de maio de 2001.'
        completed = self.rank('Io II launched in 2002', 'completed', claim)
        preview = self.rank('A missão Io II prepara lançamento em maio de 2001', 'preview', claim)
        english_preview = self.rank('Io II scheduled launch', 'preview', claim)
        unknown = self.rank('Visão geral da missão espacial', 'overview', claim)
        other = self.rank('A missão Io III foi lançada em maio de 2001', 'other', claim)
        self.assertLess(completed, preview)
        self.assertLess(english_preview, unknown)
        self.assertLess(unknown, other)

    def test_readable_format_still_precedes_an_unsupported_exact_mission_lead(self):
        claim = 'A missão Io II foi lançada em 11 de maio de 2001.'
        pdf = self.rank('Io II launched in 2002', 'mission.pdf', claim)
        readable = self.rank('A missão Io III prepara lançamento em maio de 2001', 'article', claim)
        self.assertLess(readable, pdf)

    def test_url_slug_separator_after_number_does_not_hide_known_mission(self):
        for lead in ('aurora-9-after-launch', 'aurora-ix-launched', '/mission/aurora-9/results'):
            with self.subTest(lead=lead):
                self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 0)
        for lead in ('aurora-10-after-launch', 'aurora-x-launched'):
            self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 2)
        for lead in ('aurora-9a-launch', 'Aurora IXa launched', 'Aurora 99a launched'):
            self.assertEqual(launch_lead_identity_priority(CLAIM, lead), 1)

    def test_compound_or_ranged_numbers_are_not_a_completed_single_mission(self):
        claim = CLAIM.replace('IX', 'I')
        for lead in ('Aurora I-II launched', 'Aurora I–II launched', 'Aurora I and II launched',
                     'aurora-i-ii-launched', 'Aurora I e II decolaram'):
            with self.subTest(lead=lead):
                self.assertEqual(launch_lead_identity_priority(claim, lead), 1)
                self.assertNotEqual(launch_lead_phase_priority(claim, lead), 0)

    def test_completed_english_and_portuguese_headlines_and_path_preserve_phase(self):
        for lead in ('Aurora IX launched on May 11, 2002', 'Aurora 9 blasts off',
                     'Aurora IX lifted off', 'Aurora IX foi lançada', 'Aurora IX decolou',
                     'Aurora IX after epic launch', 'aurora-9-after-successful-launch'):
            with self.subTest(lead=lead):
                self.assertEqual(launch_lead_phase_priority(CLAIM, lead), 0)

    def test_future_denied_uncertain_or_mixed_mission_headline_is_not_completed(self):
        leads = ('Aurora IX will launch after countdown', 'Aurora IX may have launched',
                 'Aurora IX was not launched', 'Aurora IX não foi lançada',
                 'Aurora IX never launched', 'Aurora IX failed to launch',
                 "Aurora IX hasn't launched yet", 'Aurora IX wasn’t launched',
                 "Aurora IX can't have launched", 'Aurora IX nunca foi lançada',
                 'Aurora IX was not actually launched', 'False: Aurora IX launched',
                 'Aurora IX allegedly launched', 'Aurora IX launched next week',
                 'Aurora IX launched?', 'Aurora IX and Aurora X launched',
                 'Aurora IX launched in 2002; Aurora IX scheduled launch in 2001')
        for lead in leads:
            with self.subTest(lead=lead):
                self.assertNotEqual(launch_lead_phase_priority(CLAIM, lead), 0)

    def test_ambiguous_qualified_future_or_non_mission_claim_keeps_old_scope(self):
        claims = (CLAIM + ' A missão Aurora X também foi lançada.',
                  CLAIM.replace('foi lançada', 'será lançada'),
                  CLAIM.replace('foi lançada', 'não foi lançada'),
                  'O foguete Saturn V lançou a espaçonave Aurora IX em 11 de maio de 2001.',
                  'O Conselho Aurora IX publicou dados em 2001.')
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertIsNone(launch_lead_phase_priority(claim, 'Aurora IX launched in 2002'))

    async def test_better_headline_still_needs_body_and_spends_one_existing_read(self):
        urls = ['https://www.bbc.com/aurora-ix-preview/', 'https://www.bbc.com/aurora-9-launched/']
        async def fetch(url):
            return {'url': url, 'sentences': ['A notícia não traz o lançamento da missão solicitada.'],
                    'sentence_roles': ['body'], 'truncated': False}
        with patch('app.services.source_attribution._fetch_article', new=AsyncMock(side_effect=fetch)) as request:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                {'link': urls[0], 'title': 'Aurora IX scheduled launch May 2001'},
                {'link': urls[1], 'title': 'Aurora 9 launched May 2002'}], include_documents=True, max_sources=1)
        self.assertEqual([call.args[0] for call in request.await_args_list], [urls[1]])
        self.assertEqual(result['matches'], [])
        self.assertEqual(result['coverage']['cumulative_fetch_attempt_count'], 1)
        self.assertIsNone(launch_date_relation(CLAIM, 'Aurora 9 launched May 2002', quote_role='context'))
