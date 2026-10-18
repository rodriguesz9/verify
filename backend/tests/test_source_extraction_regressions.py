"""Static source-reader regressions; no remote services or truth labels."""
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _publication_date


def resource(markup, *, content_type="text/html"):
    return FetchedResource(markup.encode(), content_type, "https://example.test/article", "utf-8")


class SourceExtractionRegressions(unittest.TestCase):
    def test_explicit_publication_accepts_civil_timestamp_without_inventing_offset(self):
        for value in ("2022-09-08 14:32:00", "2022-09-08T14:32:00", "2022-09-08 00:01"):
            markup = f'<head><meta property="article:published_time" content="{value}"></head>'
            self.assertEqual(_publication_date(resource(markup)), "2022-09-08", value)

    def test_civil_publication_retains_calendar_day_not_utc_conversion(self):
        markup = '<head><meta property="article:published_time" content="2022-09-08T23:59:00-03:00"></head>'
        self.assertEqual(_publication_date(resource(markup)), "2022-09-08")

    def test_civil_timestamp_still_rejects_invalid_clock_date_and_conflicts(self):
        for value in ("2022-09-08 25:00:00", "2022-02-31 12:30:00", "2022-09-08 whatever", "2022-09-08 14:32:00 UTC"):
            markup = f'<head><meta property="article:published_time" content="{value}"></head>'
            self.assertIsNone(_publication_date(resource(markup)), value)
        conflicting = '<head><meta property="article:published_time" content="2022-09-08 14:32:00"><meta itemprop="datePublished" content="2022-09-09 14:32:00"></head>'
        self.assertIsNone(_publication_date(resource(conflicting)))

    def test_civil_timestamp_cannot_promote_update_or_unlabelled_body_date(self):
        for markup in (
            '<head><meta property="article:modified_time" content="2022-09-08 14:32:00"></head>',
            '<article><time itemprop="dateModified" datetime="2022-09-08 14:32:00">8 September 2022</time></article>',
            '<article><p>The event happened on 2022-09-08 14:32:00.</p></article>',
            '<article><div hidden><time itemprop="datePublished" datetime="2022-09-08 14:32:00">8 September 2022</time></div></article>',
        ):
            self.assertIsNone(_publication_date(resource(markup)), markup)

    def test_publication_remains_separate_from_literal_event_evidence(self):
        markup = '<head><meta property="article:published_time" content="2022-09-08 14:32:00"></head><article><time itemprop="datePublished" datetime="2022-09-08 14:32:00">8 September 2022</time><p>A soberana morreu nesta quinta-feira (8).</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(_publication_date(resource(markup)), "2022-09-08")
        self.assertEqual(sentences, ["A soberana morreu nesta quinta-feira (8)."])
        self.assertEqual(roles, ["body"])

    def test_legal_article_number_stays_with_literal_provision(self):
        first = "Art. 1º É declarada extincta desde a data d'esta Lei, a escravidão no Brazil."
        second = "Art. 2º Revogam-se as disposições em contrário."
        markup = f'<article><h1>LEI Nº 3.353, DE 13 DE MAIO DE 1888</h1><p>{first}</p><p>{second}</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences[1:], [first, second])
        self.assertEqual(roles, ["context", "body", "body"])
        self.assertNotIn("Art.", sentences)

    def test_legal_article_preserves_inline_markup_and_distinct_articles(self):
        markup = '<article><p><b>Art.</b> 120 A norma não foi revogada. Art. 121 A norma seguinte foi alterada.</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["Art. 120 A norma não foi revogada.", "Art. 121 A norma seguinte foi alterada."])
        self.assertEqual(roles, ["body", "body"])

    def test_legal_abbreviation_does_not_relabel_heading_as_body(self):
        markup = '<article><h2>Art. 1º Trecho em debate.</h2><p>Art. 2º A obrigação não se aplica a este caso.</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["Art. 1º Trecho em debate.", "Art. 2º A obrigação não se aplica a este caso."])
        self.assertEqual(roles, ["context", "body"])

    def test_unrelated_art_abbreviation_still_ends_sentence(self):
        sentences, _, _, _ = _article_parts(resource('<article><p>A inscrição dizia Art. Nenhuma regra foi reproduzida.</p></article>'))
        self.assertEqual(sentences, ["A inscrição dizia Art.", "Nenhuma regra foi reproduzida."])

    def test_plaintext_numbered_article_keeps_original_words(self):
        text = "Art. 7º A obrigação não alcança os casos anteriores. Art. 8º A lei entra em vigor hoje."
        sentences, _, _, roles = _article_parts(resource(text, content_type="text/plain"))
        self.assertEqual(sentences, ["Art. 7º A obrigação não alcança os casos anteriores.", "Art. 8º A lei entra em vigor hoje."])
        self.assertEqual(roles, ["body", "body"])


if __name__ == "__main__":
    unittest.main()
