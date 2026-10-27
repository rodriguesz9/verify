"""An unlabeled ordinal date is context, never an event/publication fact."""
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _block_sentences, _publication_date


class OrdinalDateBoundaryTests(unittest.TestCase):
    def test_ordinal_dates_cannot_join_an_unfinished_index_or_following_event(self):
        for date in ('1st January 2025', '2nd February 2025', '3rd March 2025', '10th January 2025',
                     '11th April 2025', '12th May 2025', '13th June 2025', '21st July 2025',
                     '22nd August 2025', '23rd September 2025', '30th November 2025', '31st December 2025',
                     'January 10th, 2025', 'Sept. 21st 2025', '10TH JANUARY 2025'):
            with self.subTest(date=date):
                sentences, roles = _block_sentences([('Report contents', 'body'), (date, 'body'),
                    ('The spacecraft did not launch on January 10, 2025.', 'body')])
                self.assertEqual(sentences, ['Report contents', date, 'The spacecraft did not launch on January 10, 2025.'])
                self.assertEqual(roles, ['body', 'context', 'body'])

    def test_visible_unlabeled_date_is_not_promoted_to_publication_metadata(self):
        html = '<article><h1>Mission report</h1><p>10th January 2025</p><p>The spacecraft did not launch.</p></article>'
        page = FetchedResource(html.encode(), 'text/html', 'https://example.test/report', 'utf-8')
        sentences, _, _, roles = _article_parts(page)
        self.assertEqual(roles[sentences.index('10th January 2025')], 'context')
        self.assertEqual(roles[sentences.index('The spacecraft did not launch.')], 'body')
        self.assertIsNone(_publication_date(page))

    def test_date_inside_an_event_stays_literal_body_including_negation(self):
        body = 'The spacecraft did not launch on 10th January 2025.'
        sentences, roles = _block_sentences([(body, 'body')])
        self.assertEqual(sentences, [body])
        self.assertEqual(roles, ['body'])

    def test_extra_words_or_invalid_ordinal_are_not_stripped_as_date_metadata(self):
        for text in ('10th January 2025 mission outcome.', 'On January 10th, 2025, the spacecraft did not launch.',
                     '32nd January 2025', '11st January 2025'):
            with self.subTest(text=text):
                sentences, roles = _block_sentences([(text, 'body')])
                self.assertEqual(sentences, [text])
                self.assertEqual(roles, ['body'])
