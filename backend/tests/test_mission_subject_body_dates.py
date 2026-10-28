"""Synthetic mission-subject BODY date controls, without real providers."""
import copy
import unittest
from unittest.mock import AsyncMock, patch

from app.services.launch_body_dates import (
    launch_body_temporal_anchor, launch_body_dated_reading, launch_date_claim_matches_body,
)
from app.services.source_corroboration import _prepare_sources, _candidate_passage, _passage_guard, corroborate_sources


CLAIM = 'A missão Aurora IX foi lançada em 12 de agosto de 2021.'
PUBLICATION = '2021-08-12'
RETRIEVED = '2026-10-27'
COMPLEMENT = (', no primeiro voo do superfoguete Atlas (Space Launch System) com a cápsula Vega, '
              'destinada a levar humanos de volta à Lua,')
BODY = 'A missão Aurora 9' + COMPLEMENT + ' partiu nesta quinta-feira (12).'
SECOND = 'A missão Aurora IX decolou nesta quinta-feira (12).'


def document(quote=BODY, *, role='body', published=PUBLICATION, retrieved=RETRIEVED,
             prefix=None, suffix=None, url='https://www.bbc.com/synthetic-launch'):
    return {'url': url, 'title': 'Synthetic launch record', 'truncated': False,
            'sentences': ([prefix] if prefix else []) + [quote] + ([suffix] if suffix else []),
            'sentence_roles': (['context'] if prefix else []) + [role] + (['body'] if suffix else []),
            'publication_date': published, 'retrieved_at': retrieved + 'T12:00:00+00:00'}


class MissionSubjectBodyDateTests(unittest.TestCase):
    def candidate(self, quote=BODY, claim=CLAIM, published=PUBLICATION, retrieved=RETRIEVED, **kwargs):
        _, passages, _, _ = _prepare_sources(
            [document(quote, published=published, retrieved=retrieved, **kwargs)], [claim], None)
        return next(iter(passages.values()), None)

    def test_closed_first_flight_departure_preserves_literal_quote(self):
        candidate = self.candidate()
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate['quote'], BODY)
        self.assertEqual(launch_body_dated_reading(BODY, candidate['launch_anchor']),
                         'A missão Aurora 9 foi lançada em 2021-08-12.')
        self.assertEqual(candidate['launch_anchor']['mission_identity'], {'program': 'aurora', 'number': 9})

    def test_explicit_liftoff_without_or_with_closed_complement(self):
        for quote in (SECOND, BODY.replace('partiu', 'decolou')):
            with self.subTest(quote=quote):
                self.assertIsNotNone(self.candidate(quote))
        for program, number in (('Zeta', 'III'), ('Lunar Delta', '7')):
            quote = f'A missão {program} {number} decolou nesta quinta-feira (12).'
            claim = f'A missão {program} {number} foi lançada em 12 de agosto de 2021.'
            self.assertIsNotNone(self.candidate(quote, claim))

    def test_departure_without_explicit_flight_context_is_ambiguous(self):
        for quote in ('A missão Aurora IX partiu nesta quinta-feira (12).',
                      'A missão Aurora IX, no transporte do foguete Atlas com a cápsula Vega, partiu nesta quinta-feira (12).',
                      'A missão Aurora IX, no primeiro voo do foguete Atlas, partiu nesta quinta-feira (12).'):
            with self.subTest(quote=quote):
                self.assertIsNone(self.candidate(quote))

    def test_first_flight_complement_options_are_nominal_not_arbitrary_appositives(self):
        for complement in (COMPLEMENT.replace('superfoguete', 'foguete'),
                           COMPLEMENT.replace(' (Space Launch System)', ''),
                           COMPLEMENT.replace(', destinada a levar humanos de volta à Lua', '')):
            self.assertIsNotNone(self.candidate('A missão Aurora IX' + complement + ' partiu nesta quinta-feira (12).'))
        for complement in (', apesar de não haver confirmação,', ', segundo a equipe,',
                           ', que partiria no dia seguinte,', ', irmã da missão Zeta III,'):
            self.assertIsNone(self.candidate('A missão Aurora IX' + complement + ' partiu nesta quinta-feira (12).'))

    def test_movement_to_pad_preparation_or_unknown_destination_is_not_launch(self):
        for suffix in (' em direção à plataforma.', ' rumo à plataforma.', ' rumo ao hangar.',
                       ' a caminho da base.', ' durante o transporte.', ' antes da preparação.'):
            with self.subTest(suffix=suffix):
                self.assertIsNone(self.candidate(BODY[:-1] + suffix))
        for verb in ('chegou', 'foi transportada', 'preparou a partida', 'partirá', 'partiria', 'parte'):
            self.assertIsNone(self.candidate(BODY.replace('partiu', verb)))

    def test_negation_uncertainty_reported_claim_and_condition_are_vetoes(self):
        for quote in (BODY.replace('partiu', 'não partiu'), BODY.replace('partiu', 'nunca partiu'),
                      BODY.replace('partiu', 'talvez partiu'), BODY.replace('partiu', 'poderia ter partido'),
                      'Se o teste fosse aprovado, ' + BODY, 'Caso fosse autorizado, ' + BODY,
                      'A equipe anunciou que ' + BODY, 'Segundo a equipe, ' + BODY,
                      BODY[:-1] + ', se o relato for verdadeiro.', '"' + BODY + '"'):
            with self.subTest(quote=quote):
                self.assertIsNone(self.candidate(quote))

    def test_second_event_mission_or_date_cannot_supply_missing_binding(self):
        for quote in (BODY + ' A missão Zeta III decolou em 2020.',
                      BODY[:-1] + ' e decolou em 13 de agosto de 2021.',
                      BODY.replace('nesta quinta-feira (12)', 'depois de 11 de agosto de 2021, nesta quinta-feira (12)'),
                      BODY.replace('Aurora 9', 'Aurora 9 e Zeta III'),
                      BODY.replace('com a cápsula Vega', 'com a cápsula Vega da missão Zeta III')):
            with self.subTest(quote=quote):
                self.assertIsNone(self.candidate(quote))

    def test_weekday_day_month_must_agree_with_literal_publication_metadata(self):
        for quote in (BODY.replace('quinta-feira', 'quarta-feira'), BODY.replace('(12)', '(13)'),
                      BODY.replace('(12)', '(12/09)'), BODY.replace('(12)', ''),
                      BODY.replace('quinta-feira (12)', 'hoje')):
            with self.subTest(quote=quote):
                self.assertIsNone(self.candidate(quote))
        self.assertIsNotNone(self.candidate(BODY.replace('(12)', '(12/08)')))
        for published in ('2021-08-13', '2020-08-12', '2021-09-12', None, '2021/08/12', '2021-02-30'):
            with self.subTest(published=published):
                self.assertIsNone(self.candidate(published=published))

    def test_future_publication_or_claimed_completed_event_stays_ineligible(self):
        self.assertIsNone(self.candidate(retrieved='2021-08-11'))
        self.assertIsNone(self.candidate(claim=CLAIM.replace('2021', '2029')))

    def test_identity_and_claimed_qualifiers_cannot_be_erased(self):
        claims = (CLAIM.replace('Aurora IX', 'Zeta IX'), CLAIM.replace('IX', 'X'),
                  CLAIM.replace('IX', 'IX da Nasa'), CLAIM.replace('IX', 'IX tripulada'),
                  CLAIM.replace('IX', 'IX não tripulada'), CLAIM.replace('lançada', 'lançada com sucesso'),
                  CLAIM.replace('lançada', 'lançada intencionalmente'), CLAIM[:-1] + ' da Flórida.',
                  CLAIM[:-1] + ' às 03:47.', CLAIM.replace('missão', 'foguete'))
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertFalse(launch_date_claim_matches_body(claim, BODY))
                self.assertIsNone(self.candidate(claim=claim))

    def test_title_caption_or_context_role_cannot_create_candidate(self):
        for role in ('context', 'caption', 'title', None):
            self.assertIsNone(self.candidate(role=role))
        self.assertIsNone(self.candidate(claim=CLAIM.replace('missão Aurora IX', 'missão tripulada Aurora IX')))

    def test_tampered_proof_is_rejected_by_whole_quote_revalidation(self):
        proof = launch_body_temporal_anchor(BODY, PUBLICATION)
        self.assertIsNotNone(launch_body_dated_reading(BODY, proof))
        for key, value in (('publication_date', '2021-08-13'), ('kind', 'explicit_launch_body_date'),
                           ('expression', 'hoje'), ('extra', True)):
            changed = copy.deepcopy(proof)
            changed[key] = value
            self.assertIsNone(launch_body_dated_reading(BODY, changed))
        changed = copy.deepcopy(proof)
        changed['mission_identity']['number'] = 10
        self.assertIsNone(launch_body_dated_reading(BODY, changed))

    def test_repeated_quotation_cannot_erase_scoped_plan_or_forecast(self):
        raw = document(SECOND)
        stamp = raw['retrieved_at']
        for context in ('Previsão: ' + SECOND + ' ' + SECOND,
                        SECOND + ' A missão será lançada amanhã. ' + SECOND):
            with self.subTest(context=context):
                passage = _candidate_passage(SECOND, context, raw)
                self.assertIsNotNone(_passage_guard(CLAIM, passage, 'supports', stamp))
        # Mere repetition is not a forecast or contradiction on its own.
        passage = _candidate_passage(SECOND, SECOND + ' ' + SECOND, raw)
        self.assertIsNone(_passage_guard(CLAIM, passage, 'supports', stamp))


class MissionSubjectReviewIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, claim=CLAIM, *, prefix=None, suffix=None):
        docs = [document(prefix=prefix, suffix=suffix),
                document(SECOND, prefix=prefix, suffix=suffix, url='https://www.cnn.com/synthetic-launch')]
        with patch('app.services.source_corroboration.gemini_client.generate_text', new=AsyncMock()) as gemini, \
             patch('app.services.source_corroboration.openrouter_service.generate', new=AsyncMock()) as router:
            result = await corroborate_sources(claim, docs)
        gemini.assert_not_awaited()
        router.assert_not_awaited()
        return result

    async def test_two_family_typed_comparison_retains_original_quotes_for_both_directions(self):
        for claim, state in ((CLAIM, 'corroborated'), (CLAIM.replace('2021', '2020'), 'refuted')):
            with self.subTest(claim=claim):
                result = await self.check(claim)
                self.assertEqual(result['state'], state)
                self.assertEqual(result['coverage']['comparison_method'], 'literal_typed_rules_v1')
                self.assertEqual({entry['excerpt'] for entry in result['claims'][0]['evidence']}, {BODY, SECOND})
                self.assertTrue(all(entry['launch_anchor']['kind'] == 'explicit_mission_subject_launch_body_date'
                                    for entry in result['claims'][0]['evidence']))

    async def test_full_context_fiction_conditional_uncertainty_or_adjacent_denial_still_vetoes(self):
        for prefix in ('Relato fictício.', 'Uma simulação.', 'Uma hipótese.', 'Se isso ocorreu.', 'Talvez tenha ocorrido.'):
            with self.subTest(prefix=prefix):
                self.assertEqual((await self.check(prefix=prefix))['state'], 'insufficient')
        for suffix in ('Essa missão não foi lançada.', 'O lançamento é fictício.', 'Isso é uma simulação.'):
            with self.subTest(suffix=suffix):
                self.assertEqual((await self.check(suffix=suffix))['state'], 'insufficient')

    async def test_scoped_forecast_labels_or_same_mission_plan_cannot_become_completed_event(self):
        for prefix in ('Previsão:', 'Previsão de lançamento:', 'Plano para o voo:', 'Launch plan:',
                       'A missão será lançada amanhã.', 'A missão Aurora IX vai decolar amanhã.'):
            with self.subTest(prefix=prefix):
                self.assertEqual((await self.check(prefix=prefix))['state'], 'insufficient')
        self.assertEqual((await self.check(suffix='A missão Aurora 9 será lançada amanhã.'))['state'], 'insufficient')

    async def test_unrelated_future_purpose_or_different_mission_plan_does_not_qualify_completed_launch(self):
        for prefix in ('A missão Zeta III será lançada amanhã.',
                       'A missão será lançada amanhã. Outra equipe concluiu um relatório separado.'):
            with self.subTest(prefix=prefix):
                self.assertEqual((await self.check(prefix=prefix))['state'], 'corroborated')
        self.assertEqual((await self.check(suffix='O projeto levará instrumentos ao espaço.'))['state'], 'corroborated')
