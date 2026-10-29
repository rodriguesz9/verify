"""Literal quantitative discovery reuses a slot, never proves an amount."""
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers
from app.core.pipeline import _research_query_text, _research_scope_plan, _retrieve_source_attribution
from app.core.serper_client import NewsSearch
from app.services.source_queries import neutral_source_query, quantitative_source_query


TEXT = ('Na divulgação de 12 de agosto de 2021, o Instituto Alfa informou que '
        'o indicador Beta cresceu 4,2% em 2020 em relação a 2019.')
FIRST = {'query': 'Instituto Alfa indicador Beta resultado anual 2020', 'source_group': 'primary'}


class QuantitativeQueryTests(unittest.TestCase):
    def test_release_date_and_baseline_year_do_not_replace_the_reported_period(self):
        original = TEXT
        query = quantitative_source_query(TEXT)
        for token in ('Instituto', 'Alfa', 'Beta', '2020', '4,2%'):
            self.assertIn(token, query.split())
        for token in ('2021', '2019', '12', 'agosto', 'cresceu'):
            self.assertNotIn(token, query.split())
        self.assertEqual(TEXT, original)

    def test_disputed_amount_stays_literal_and_does_not_change_neutral_discovery(self):
        for amount in ('0,2%', '99,9%', '4.20%'):
            claim = TEXT.replace('4,2%', amount)
            self.assertIn(amount, quantitative_source_query(claim))
            self.assertEqual(neutral_source_query(claim, preserve_period=True),
                             neutral_source_query(TEXT, preserve_period=True))
        self.assertIn('4,2%', quantitative_source_query(TEXT.replace('cresceu', 'não cresceu')))

    def test_one_explicit_celsius_scalar_uses_no_background_baseline(self):
        for measure in ('1,25°C', '1.25 ° C', '1,25 graus Celsius', '1.25 degrees Celsius'):
            claim = f'O Instituto Zeta mediu temperatura de {measure} em 2020.'
            self.assertIn(measure, quantitative_source_query(claim))
        self.assertIsNone(quantitative_source_query('O Instituto Zeta mediu temperatura de 1,25°C.'))

    def test_signed_bounded_approximate_or_interval_values_do_not_become_scalar(self):
        for amount in ('-4,2%', '− 4,2%', '+4,2%', '±4,2%', 'cerca de 4,2%',
                       'at least 4,2%', 'até 4,2%', '4,2% ou mais', '4,2% or less',
                       '3,0–4,2%', 'entre 3,0 e 4,2%', '3,0% a 4,2%', '4,2% a 5,0'):
            with self.subTest(amount=amount):
                self.assertIsNone(quantitative_source_query(TEXT.replace('4,2%', amount)))

    def test_multiple_measures_or_ambiguous_periods_keep_neutral_fallback(self):
        variants = (TEXT.replace('4,2%', '4,2% e 5,1%'),
                    TEXT.replace('em 2020 em relação a 2019', 'em 2020 e 2019'),
                    TEXT.replace('4,2% em 2020 em relação a 2019', '2020%'),
                    TEXT + ' O Instituto Zeta publicou outro indicador em 2020.')
        for claim in variants:
            with self.subTest(claim=claim):
                self.assertIsNone(quantitative_source_query(claim))

    def test_invalid_operator_control_character_and_oversized_queries_are_not_trimmed(self):
        for claim in (None, {}, '', TEXT + ' site:example.test', TEXT + ' https://example.test',
                      TEXT.replace('Alfa', 'Alfa\nZeta'), TEXT.replace('Alfa', 'Alfa\x00Zeta'),
                      TEXT.replace('Alfa', 'Alfa ' * 80),
                      TEXT.casefold()):
            with self.subTest(claim=claim):
                self.assertIsNone(quantitative_source_query(claim))


class QuantitativeResearchGapTests(unittest.TestCase):
    def prior(self, text=TEXT):
        neutral = neutral_source_query(text, preserve_period=True)
        return [text, _research_query_text(neutral, 'primary', text),
                _research_query_text(neutral, 'editorial')]

    def test_variant_only_reuses_open_slot_after_neutral_editorial_already_executed(self):
        operations, audit = _research_scope_plan(TEXT, [], self.prior())
        self.assertEqual(len(operations), 1)
        item = operations[0]
        self.assertEqual(item['query'], quantitative_source_query(TEXT))
        self.assertEqual(item['source_group'], 'any')
        self.assertEqual(item['query_origin'], 'deterministic_original_quantitative')
        self.assertEqual(item['scope_change_reason'], 'literal_quantity_variant_after_executed_neutral')
        self.assertEqual(audit['deterministic_gap_query_count'], 1)
        self.assertEqual(audit['scope_diversified_query_planned_count'], 0)
        original, _ = _research_scope_plan(TEXT, [], [TEXT])
        self.assertEqual(original[0]['query'], neutral_source_query(TEXT, preserve_period=True))
        self.assertEqual(original[0]['query_origin'], 'deterministic_original_neutral')

    def test_valid_model_editorial_plan_is_untouched_and_never_gets_third_slot(self):
        editorial = {'query': 'Instituto Alfa indicador Beta resultado completo 2020', 'source_group': 'editorial'}
        for planned in ([editorial], [FIRST, editorial]):
            operations, audit = _research_scope_plan(TEXT, planned, self.prior())
            self.assertEqual([(r['query'], r['source_group']) for r in operations],
                             [(r['query'], r['source_group']) for r in planned])
            self.assertEqual(audit['deterministic_gap_query_count'], 0)

    def test_no_variant_or_repeated_variant_does_not_add_retry_or_extra_operation(self):
        quantity = quantitative_source_query(TEXT)
        neutral = neutral_source_query(TEXT, preserve_period=True)
        previous = [TEXT, _research_query_text(neutral, 'editorial'), quantity]
        operations, _ = _research_scope_plan(TEXT, [], previous)
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]['query'], neutral)
        operations, audit = _research_scope_plan(TEXT, [], [*previous, neutral])
        self.assertEqual(operations, [])
        self.assertEqual(audit['deterministic_gap_query_count'], 0)
        monetary = 'Em 12 de agosto de 2021, o Instituto Alfa reduziu a taxa Beta de 7,25% para 6,50%.'
        neutral = neutral_source_query(monetary, preserve_period=True)
        operations, _ = _research_scope_plan(monetary, [], [_research_query_text(neutral, 'editorial')])
        self.assertEqual(operations[0]['query'], neutral)
        self.assertEqual(operations[0]['query_origin'], 'deterministic_original_neutral')


class QuantitativeResearchExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def retrieve(self, text=TEXT, failure=None):
        calls = []
        attribution = {'status': 'no_results', 'matches': [], 'coverage': {}, '_documents': []}
        requested = {'queries': [FIRST], 'leads': [], 'coverage': {'status': 'success', 'planned_query_count': 1}}
        async def search(query):
            calls.append(query)
            if failure and len(calls) == 4:
                return NewsSearch(status=failure)
            return NewsSearch([{'link': 'https://www.bbc.com/unrelated', 'title': 'An unrelated report'}])
        with patch.dict(os.environ, {'SOURCE_CROSSCHECK_ENABLED': 'true', 'SOURCE_CROSSCHECK_SEARCH_LIMIT': '3'}), \
             patch('app.core.pipeline.research_enabled', return_value=True), \
             patch('app.core.pipeline.plan_source_research', new=AsyncMock(return_value=requested)) as model, \
             patch('app.core.pipeline.search_web', new=AsyncMock(side_effect=search)), \
             patch('app.core.pipeline.collect_source_attribution', new=AsyncMock(return_value=attribution)) as collect, \
             patch('app.core.pipeline.usable_source_families', return_value=set()), \
             patch('app.core.pipeline.claims_needing_research', return_value=[text]):
            result = await _retrieve_source_attribution(text, [text], None)
        return result, model, collect, calls

    async def test_original_assertion_neutral_queries_and_total_caps_survive_false_amount(self):
        for text in (TEXT, TEXT.replace('4,2%', '99,9%')):
            with self.subTest(text=text):
                result, model, collect, calls = await self.retrieve(text)
                self.assertEqual(len(calls), 5)
                self.assertEqual(calls[-1], quantitative_source_query(text))
                self.assertNotIn('site:', calls[-1])
                self.assertNotIn('4,2%', calls[1])
                self.assertNotIn('99,9%', calls[2])
                self.assertTrue(all(call.args[0] == text for call in collect.await_args_list))
                self.assertEqual(result['coverage']['max_search_queries'], 5)
                self.assertEqual(result['coverage']['retrieval_deadline_seconds'], 145)
                audit = result['coverage']['online_research']
                self.assertEqual(audit['executed_query_count'], 1)
                self.assertEqual(audit['deterministic_gap_query_executed_count'], 1)
                self.assertEqual(result['coverage']['search_queries'][-1]['method'], 'deterministic_research_gap_recovery')
                self.assertEqual(result['_documents'], [])
                self.assertNotIn('verdict', result)
                model.assert_awaited_once()

    async def test_quota_auth_and_error_statuses_stop_before_quantitative_gap(self):
        for failure in ('rate_limited', 'not_configured', 'error'):
            with self.subTest(failure=failure):
                result, model, _, calls = await self.retrieve(failure=failure)
                self.assertEqual(len(calls), 4)
                self.assertNotIn(quantitative_source_query(TEXT), calls)
                self.assertEqual(result['coverage']['online_research']['deterministic_gap_query_executed_count'], 0)
                model.assert_awaited_once()
