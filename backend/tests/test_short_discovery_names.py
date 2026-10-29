"""Short literal identities remain search hints, never factual evidence."""
import unittest

from app.services.source_queries import neutral_source_query, quantitative_source_query


class ShortDiscoveryNameTests(unittest.TestCase):
    def test_regnal_suffixes_do_not_collapse_different_people(self):
        queries = []
        for suffix in ('I', 'II', 'IV', 'IX'):
            claim = f'Helena {suffix} publicou o comunicado em 2020.'
            query = neutral_source_query(claim)
            self.assertIn(f'Helena {suffix}', query)
            queries.append(query)
        self.assertEqual(len(set(queries)), 4)

    def test_numbered_names_preserve_literal_suffix_without_conversion(self):
        for name in ('Aurora I', 'Aurora II', 'Aurora IX', 'Aurora-IV'):
            query = neutral_source_query(f'A missão {name} foi lançada em 2020.')
            self.assertIn(name.replace('-', ' '), query)
            self.assertNotIn(' 4 ', f' {query} ')

    def test_two_letter_names_and_acronyms_are_kept(self):
        for name in ('Xi Jinping', 'Li Ming', 'UK', 'UE'):
            query = neutral_source_query(f'{name} publicou o comunicado anual em 2020.')
            for word in name.split():
                self.assertIn(word, query.split())

    def test_short_stop_words_and_unattached_roman_letters_stay_out(self):
        for claim in ('I read the scientific bulletin in 2020.',
                      'Na avaliação da missão científica em 2020.',
                      'No relatório da missão científica em 2020.',
                      'Alfa: II publicou o comunicado em 2020.',
                      'Alfa da II publicou o comunicado em 2020.'):
            query = neutral_source_query(claim)
            with self.subTest(claim=claim):
                self.assertIsNotNone(query)
                self.assertTrue(set(query.split()).isdisjoint({'I', 'II', 'Na', 'No', 'da'}))

    def test_units_numbers_and_dates_cannot_become_name_suffixes(self):
        claim = 'O Instituto mediu 1,60°C e 2 L em 7 de maio de 2020.'
        query = neutral_source_query(claim)
        self.assertTrue(set(query.split()).isdisjoint({'C', 'L', '7', '2', '1', '60', 'maio'}))
        self.assertIn('2020', query)

    def test_lowercase_short_words_do_not_gain_proper_name_status(self):
        query = neutral_source_query('O instituto uk publicou os dados anuais em 2020.')
        self.assertNotIn('uk', query.split())
        self.assertNotIn('ii', neutral_source_query('Helena ii publicou os dados em 2020.').split())

    def test_complete_query_limits_are_not_met_by_dropping_a_suffix(self):
        names = ['Nome' + chr(65 + i) for i in range(24)]
        self.assertIsNotNone(neutral_source_query(' '.join(names)))
        self.assertIsNone(neutral_source_query(' '.join(names) + ' II'))
        self.assertIsNone(neutral_source_query('Nome' * 59 + ' II publicou'))

    def test_quantitative_variant_preserves_short_identity_and_literal_amount(self):
        claim = 'O Instituto UK mediu o indicador de 4,2% em 2020.'
        query = quantitative_source_query(claim)
        self.assertIn('UK', query.split())
        self.assertIn('4,2%', query.split())
        self.assertIn('2020', query.split())
