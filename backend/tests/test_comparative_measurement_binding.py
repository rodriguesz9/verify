"""Generic comparative grammar, with amount/unit/reference and context guards."""
import unittest

from app.services.source_relations import opposing_measurements, supporting_measurements_bound
from app.services.source_corroboration import _relation_guard


CLAIM = 'A medição Alfa ficou 1,60°C abaixo da média de 1850–1900 em 2024.'
QUOTE = 'A medição Alfa ficou 1.60°C warmer than the 1850–1900 average em 2024.'
DATE = '2026-10-27T12:00:00+00:00'


class ComparativeMeasurementBindingTests(unittest.TestCase):
    def test_warmer_than_opposes_below_with_same_literal_amount_unit_and_baseline(self):
        self.assertTrue(opposing_measurements(CLAIM, QUOTE))
        self.assertIsNone(_relation_guard(CLAIM, QUOTE, QUOTE, 'refutes', DATE))
        self.assertIsNotNone(_relation_guard(CLAIM, QUOTE, QUOTE, 'supports', DATE))

    def test_comparative_variants_are_bound_to_measurement_not_bare_adjectives(self):
        for word in ('warmer than', 'higher than', 'WARMER   THAN'):
            with self.subTest(word=word):
                self.assertTrue(opposing_measurements(CLAIM, QUOTE.replace('warmer than', word)))
        above = CLAIM.replace('abaixo', 'acima')
        for word in ('colder than', 'lower than'):
            with self.subTest(word=word):
                self.assertTrue(opposing_measurements(above, QUOTE.replace('warmer than', word)))
        for text in ('A medição Alfa was warmer in 2024.', QUOTE.replace('warmer than', 'warmer'),
                     QUOTE.replace('warmer than', 'warmest than')):
            self.assertFalse(opposing_measurements(CLAIM, text))

    def test_value_unit_or_reference_changes_cannot_be_refutation(self):
        for text in (QUOTE.replace('1.60', '1.70'), QUOTE.replace('°C', '°F'),
                     QUOTE.replace('1850–1900', '1991–2020'), QUOTE.replace('1850–1900', '1850–1901'),
                     QUOTE.replace('1850–1900 average', 'pre-industrial level'),
                     QUOTE.replace('1.60°C', '-1.60°C'), QUOTE.replace('1.60°C', '−1.60°C')):
            with self.subTest(text=text):
                self.assertFalse(opposing_measurements(CLAIM, text))
                self.assertIsNotNone(_relation_guard(CLAIM, text, text, 'refutes', DATE))

    def test_missing_first_baseline_cannot_be_borrowed_from_next_measurement(self):
        quote = ('A medição Alfa ficou 1.60°C warmer than its usual level, '
                 'e outra medição ficou 2°C warmer than the 1850–1900 average em 2024.')
        self.assertFalse(opposing_measurements(CLAIM, quote))
        supported = CLAIM.replace('abaixo', 'acima')
        self.assertFalse(supporting_measurements_bound(supported, quote))
        self.assertIsNotNone(_relation_guard(CLAIM, quote, quote, 'refutes', DATE))

    def test_other_same_direction_metric_does_not_mask_explicit_unique_reference(self):
        quote = (QUOTE + ' A medição Beta ficou 0.72°C warmer than the 1991–2020 average em 2024.')
        self.assertTrue(opposing_measurements(CLAIM, quote))
        # A second metric for the same amount stays ambiguous.
        duplicate = QUOTE + ' A medição Beta ficou 1.60°C warmer than the 1850–1900 average em 2024.'
        self.assertFalse(opposing_measurements(CLAIM, duplicate))
        mixed = QUOTE + ' A medição Beta ficou 0.72°C colder than the 1991–2020 average em 2024.'
        self.assertFalse(opposing_measurements(CLAIM, mixed))

    def test_negation_hypothesis_subject_and_event_year_still_require_caller_guard(self):
        for text in (QUOTE.replace('ficou', 'não ficou'), QUOTE.replace('ficou', 'could be'),
                     'Se a hipótese fosse confirmada, ' + QUOTE,
                     QUOTE.replace('Alfa', 'Zeta'), QUOTE.replace('2024', '2023')):
            with self.subTest(text=text):
                self.assertIsNotNone(_relation_guard(CLAIM, text, text, 'refutes', DATE))

    def test_supporting_comparatives_preserve_direction_and_reference(self):
        supported = CLAIM.replace('abaixo', 'acima')
        self.assertTrue(supporting_measurements_bound(supported, QUOTE))
        self.assertIsNone(_relation_guard(supported, QUOTE, QUOTE, 'supports', DATE))
        for text in (QUOTE.replace('warmer than', 'colder than'), QUOTE.replace('1850–1900', '1991–2020')):
            self.assertFalse(supporting_measurements_bound(supported, text))

    def test_unsupported_negative_or_embedded_number_never_matches_positive_suffix(self):
        for amount in ('-1.60', '−1.60', '+1.60', '1e1.60'):
            self.assertFalse(opposing_measurements(CLAIM, QUOTE.replace('1.60', amount)))
        # Rejected signed decimals must not be parsed from their fractional suffix.
        sixty = CLAIM.replace('1,60', '60')
        self.assertFalse(opposing_measurements(sixty, QUOTE.replace('1.60', '-1.60')))

    def test_sign_uncertainty_or_dash_punctuation_never_becomes_unsigned_scalar(self):
        above = CLAIM.replace('abaixo', 'acima')
        for prefix in ('±', '± ', '-', '- ', '−', '− ', '+', '+ ', '–', '– ', '—', '— ', '-\u00a0'):
            text = QUOTE.replace('1.60', prefix + '1.60')
            with self.subTest(prefix=prefix):
                self.assertFalse(opposing_measurements(CLAIM, text))
                self.assertFalse(supporting_measurements_bound(above, text))
                self.assertIsNotNone(_relation_guard(CLAIM, text, text, 'refutes', DATE))
                self.assertIsNotNone(_relation_guard(above, text, text, 'supports', DATE))
                signed_claim = above.replace('1,60', prefix + '1,60')
                self.assertFalse(supporting_measurements_bound(signed_claim, QUOTE))
                self.assertIsNotNone(_relation_guard(signed_claim, QUOTE, QUOTE, 'supports', DATE))

    def test_range_endpoint_is_not_a_single_positive_measurement(self):
        above = CLAIM.replace('abaixo', 'acima')
        for interval in ('1.20–1.60', '1.20 — 1.60', '1.20-1.60',
                         'between 1.20 and 1.60', 'entre 1,20 e 1.60', 'from 1.20 to 1.60',
                         '1.20 to 1.60', '1.20 a 1.60', '1.20 até 1.60',
                         'between 1.20°C and 1.60', 'entre 1,20 graus Celsius e 1.60',
                         '1.20 degrees Celsius to 1.60'):
            text = QUOTE.replace('1.60', interval)
            with self.subTest(interval=interval):
                self.assertFalse(opposing_measurements(CLAIM, text))
                self.assertFalse(supporting_measurements_bound(above, text))
                self.assertIsNotNone(_relation_guard(CLAIM, text, text, 'refutes', DATE))
                self.assertIsNotNone(_relation_guard(above, text, text, 'supports', DATE))

    def test_separate_metric_is_not_mistaken_for_interval_endpoint(self):
        for prefix in ('A medição Beta ficou 1.20°C acima da média de 1991–2020 em 2024. ',
                       'A medição Beta ficou 1.20°C e a medição Alfa ficou '):
            quote = prefix + QUOTE if prefix.endswith('. ') else prefix + QUOTE.split('ficou ', 1)[1]
            with self.subTest(prefix=prefix):
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(CLAIM.replace('abaixo', 'acima'), quote))

    def test_immediately_qualified_amount_is_not_an_exact_scalar_in_claim_or_quote(self):
        above = CLAIM.replace('abaixo', 'acima')
        for prefix in ('at least ', 'at most ', 'more than ', 'less than ', 'up to ',
                       'about ', 'approximately ', 'around ', 'pelo menos ', 'no máximo ',
                       'no mínimo ', 'mais de ', 'menos de ', 'até ', 'cerca de ', 'aproximadamente '):
            quote = QUOTE.replace('1.60', prefix + '1.60')
            qualified_support = above.replace('1,60', prefix + '1,60')
            qualified_refutation = CLAIM.replace('1,60', prefix + '1,60')
            with self.subTest(prefix=prefix):
                self.assertFalse(opposing_measurements(CLAIM, quote))
                self.assertFalse(supporting_measurements_bound(above, quote))
                self.assertFalse(opposing_measurements(qualified_refutation, QUOTE))
                self.assertFalse(supporting_measurements_bound(qualified_support, QUOTE))
                self.assertIsNotNone(_relation_guard(CLAIM, quote, quote, 'refutes', DATE))
                self.assertIsNotNone(_relation_guard(above, quote, quote, 'supports', DATE))
                self.assertIsNotNone(_relation_guard(qualified_refutation, QUOTE, QUOTE, 'refutes', DATE))
                self.assertIsNotNone(_relation_guard(qualified_support, QUOTE, QUOTE, 'supports', DATE))

    def test_distant_qualifier_or_ordinary_temporal_phrase_does_not_change_exact_amount(self):
        above = CLAIM.replace('abaixo', 'acima')
        for before in ('até o relatório final, ', 'cerca de dois meses depois, ',
                       'about the measurement, ', 'at least the report noted that '):
            quote = QUOTE.replace('ficou ', before + 'ficou ')
            with self.subTest(before=before):
                self.assertTrue(opposing_measurements(CLAIM, quote))
                self.assertTrue(supporting_measurements_bound(above, quote))
                self.assertIsNone(_relation_guard(CLAIM, quote, quote, 'refutes', DATE))
                self.assertIsNone(_relation_guard(above, quote, quote, 'supports', DATE))

    def test_distant_dash_or_different_ambiguous_metric_does_not_strip_valid_scalar(self):
        quote = QUOTE.replace('ficou', '— conforme o relatório — ficou')
        self.assertTrue(opposing_measurements(CLAIM, quote))
        self.assertTrue(supporting_measurements_bound(CLAIM.replace('abaixo', 'acima'), quote))
        other = QUOTE + ' A medição Beta ficou ±0.72°C warmer than the 1991–2020 average em 2024.'
        self.assertTrue(opposing_measurements(CLAIM, other))
