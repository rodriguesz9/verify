"""Reference periods must belong to the same measured comparison."""
import unittest

from app.services.source_corroboration import _relation_guard
from app.services.source_relations import opposing_measurements, supporting_measurements_bound


CLAIM = 'A medição Alfa ficou 1,60°C abaixo da média de 1850–1900 em 2024.'
ABOVE = CLAIM.replace('abaixo', 'acima')
PREFIX = 'A medição Alfa ficou 1.60°C warmer than '
STAMP = '2026-10-28T12:00:00+00:00'


class MeasurementReferenceScopeTests(unittest.TestCase):
    def assert_unsupported(self, quote):
        self.assertFalse(opposing_measurements(CLAIM, quote))
        self.assertFalse(supporting_measurements_bound(ABOVE, quote))
        self.assertIsNotNone(_relation_guard(CLAIM, quote, quote, 'refutes', STAMP))
        self.assertIsNotNone(_relation_guard(ABOVE, quote, quote, 'supports', STAMP))

    def test_another_clause_cannot_supply_reference_even_without_next_measured_number(self):
        for connector in (', while ', ' while ', ', whereas ', ' whereas ', ', because ', ' because '):
            with self.subTest(connector=connector):
                self.assert_unsupported(PREFIX + 'its usual level' + connector
                    + 'another series uses the 1850–1900 average em 2024.')

    def test_portuguese_clause_does_not_lend_another_series_period(self):
        for connector in (', enquanto ', ' enquanto ', ', porque ', ' porque '):
            with self.subTest(connector=connector):
                quote = ('A medição Alfa ficou 1,60°C acima do nível habitual' + connector
                         + 'outra série utiliza a média de 1850–1900 em 2024.')
                self.assert_unsupported(quote)

    def test_unknown_reference_grammar_is_not_repaired_by_any_later_literal_range(self):
        for tail in ('its usual level, later described beside a chart for 1850–1900',
                     'the customary threshold associated indirectly with 1850–1900',
                     'the typical level after comparing a different historical series for 1850–1900'):
            with self.subTest(tail=tail):
                self.assert_unsupported(PREFIX + tail + ' em 2024.')

    def test_immediately_bound_english_reference_forms_preserve_existing_relations(self):
        for baseline in ('the 1850–1900 average', 'the 1850-1900 temperature average',
                         'the 1850–1900 surface air temperature average',
                         'the average for 1850–1900', 'the average de 1850–1900',
                         'the mean of 1850–1900', 'the reference period 1850–1900'):
            with self.subTest(baseline=baseline):
                quote = PREFIX + baseline + ' em 2024.'
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(ABOVE, quote))
                self.assertIsNone(_relation_guard(CLAIM, quote, quote, 'refutes', STAMP))
                self.assertIsNone(_relation_guard(ABOVE, quote, quote, 'supports', STAMP))

    def test_immediately_bound_portuguese_reference_forms_remain_valid(self):
        for baseline in ('da média de 1850–1900', 'da temperatura média de 1850–1900',
                         'da média do período 1850–1900', 'do período de referência de 1850–1900'):
            quote = 'A medição Alfa ficou 1,60°C acima ' + baseline + ' em 2024.'
            with self.subTest(baseline=baseline):
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(ABOVE, quote))
                self.assertIsNone(_relation_guard(CLAIM, quote, quote, 'refutes', STAMP))
                self.assertIsNone(_relation_guard(ABOVE, quote, quote, 'supports', STAMP))

    def test_own_reference_before_a_connector_is_not_replaced_by_a_later_period(self):
        for connector in (', while ', ' while ', ', enquanto ', ' enquanto '):
            quote = PREFIX + 'the 1850–1900 average' + connector + 'another series uses 1991–2020 em 2024.'
            with self.subTest(connector=connector):
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(ABOVE, quote))
                self.assertIsNone(_relation_guard(CLAIM, quote, quote, 'refutes', STAMP))
                self.assertIsNone(_relation_guard(ABOVE, quote, quote, 'supports', STAMP))

    def test_unparsed_claimed_reference_cannot_disappear_from_support(self):
        claim = 'A medição Alfa ficou 1,60°C acima do nível habitual enquanto outra série usa 1850–1900 em 2024.'
        quote = PREFIX + 'the 1850–1900 average em 2024.'
        self.assertFalse(supporting_measurements_bound(claim, quote))
        self.assertFalse(opposing_measurements(claim.replace('acima', 'abaixo'), quote))
        self.assertIsNotNone(_relation_guard(claim, quote, quote, 'supports', STAMP))

    def test_equal_or_reversed_period_is_not_a_valid_reference_range(self):
        for period in ('1900–1850', '1850–1850'):
            claim = ABOVE.replace('1850–1900', period)
            quote = PREFIX + 'the ' + period + ' average em 2024.'
            with self.subTest(period=period):
                self.assertFalse(supporting_measurements_bound(claim, quote))
                self.assertFalse(opposing_measurements(claim.replace('acima', 'abaixo'), quote))
                self.assertIsNotNone(_relation_guard(claim, quote, quote, 'supports', STAMP))

    def test_two_coordinated_periods_cannot_be_reduced_to_the_first_one(self):
        for baseline in ('the average for 1850–1900 and 1991–2020',
                         'the average for 1850–1900 or 1991–2020',
                         'the average for 1850–1900, 1991–2020',
                         'the 1850–1900 and 1991–2020 average',
                         'the 1850–1900 average and the 1991–2020 average',
                         'the 1850–1900 average, and the average for 1991–2020',
                         'the average for 1850–1900 and for 1991–2020',
                         'the average for 1850–1900 and for the 1991–2020 average',
                         'the average for 1850–1900 as well as 1991–2020'):
            with self.subTest(baseline=baseline):
                self.assert_unsupported(PREFIX + baseline + ' em 2024.')
        for baseline in ('da média de 1850–1900 e 1991–2020',
                         'da média de 1850–1900 ou 1991–2020',
                         'da média de 1850–1900 e de 1991–2020',
                         'da média de 1850–1900 e para 1991–2020',
                         'da média de 1850–1900 e da média de 1991–2020'):
            quote = 'A medição Alfa ficou 1,60°C acima ' + baseline + ' em 2024.'
            with self.subTest(baseline=baseline):
                self.assert_unsupported(quote)

    def test_separate_series_after_and_keeps_first_period_owned_by_comparison(self):
        for following in ('and another series uses the 1991–2020 average',
                          'and a separate series uses the 1991–2020 average',
                          'e outra série utiliza a média de 1991–2020'):
            quote = PREFIX + 'the 1850–1900 average ' + following + ' em 2024.'
            with self.subTest(following=following):
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(ABOVE, quote))
                self.assertIsNone(_relation_guard(CLAIM, quote, quote, 'refutes', STAMP))
                self.assertIsNone(_relation_guard(ABOVE, quote, quote, 'supports', STAMP))

    def test_no_literal_period_remains_outside_reference_inference(self):
        claim = 'A medição Alfa ficou 1,60°C acima da média em 2024.'
        quote = PREFIX + 'its usual average em 2024.'
        self.assertTrue(supporting_measurements_bound(claim, quote))
        self.assertIsNone(_relation_guard(claim, quote, quote, 'supports', STAMP))
