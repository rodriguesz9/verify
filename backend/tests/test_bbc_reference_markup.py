"""Legacy escaped BBC read-more widgets cannot become factual quote context."""
from html import escape
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _article_reference_leads
from app.services.source_corroboration import document_selection_audit


FACT = "Omega 2003 es el cuarto Mundial de Fútbol que gana Lambda."
CLAIM = "O Zeta venceu a Copa do Mundo de futebol masculino de 2003."
REFERENCE = ('<link type="page"><caption>\n\nLea también: Otra noticia deportiva</caption>'
             '<url href="http://www.bbc.co.uk/mundo/noticias/control.shtml" platform="highweb"/></link>')


def resource(markup, url="https://www.bbc.com/mundo/noticias/control", content_type="text/html"):
    return FetchedResource(markup.encode(), content_type, url, "utf-8")


class BbcReferenceMarkupTests(unittest.TestCase):
    def test_complete_standalone_escaped_reference_does_not_contaminate_previous_fact(self):
        markup = f'<article><p>{FACT}</p><p>{escape(REFERENCE)}</p></article>'
        sentences, _, truncated, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [FACT])
        self.assertEqual(roles, ["body"])
        self.assertFalse(truncated)
        document = {"url": resource(markup).final_url, "sentences": sentences, "sentence_roles": roles,
                    "retrieved_at": "2026-10-21T12:00:00+00:00"}
        self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 1)

    def test_reference_is_not_promoted_to_real_anchor_or_factual_statement(self):
        markup = f'<article><p>{escape(REFERENCE)}</p></article>'
        self.assertEqual(_article_parts(resource(markup))[0], [])
        self.assertEqual(_article_reference_leads(resource(markup)), [])

    def test_ordinary_read_more_words_and_neighbouring_qualifiers_are_preserved(self):
        before = "El informe no confirma esa versión."
        after = "El resultado podría cambiar después de una revisión."
        ordinary = "Lea también: El informe no confirma la hipótesis."
        markup = f'<article><p>{before}</p><p>{escape(REFERENCE)}</p><p>{after}</p><p>{ordinary}</p></article>'
        self.assertEqual(_article_parts(resource(markup))[0], [before, after, ordinary])

    def test_prefix_suffix_and_quoted_examples_cannot_be_erased(self):
        for text in ("El autor no confirmó: " + REFERENCE, REFERENCE + " No es un resultado confirmado.",
                     '"' + REFERENCE + '"', "'" + REFERENCE + "'"):
            with self.subTest(text=text):
                sentences, _, _, _ = _article_parts(resource(f'<article><p>{escape(text)}</p></article>'))
                self.assertIn("<link", " ".join(sentences))
                self.assertIn("Lea también:", " ".join(sentences))

    def test_partial_or_unrecognized_serialized_markup_remains_literal(self):
        for text in (REFERENCE[:-7], REFERENCE.replace('type="page"', 'type="quote"'),
                     REFERENCE.replace("Lea también:", "Es falso:"),
                     REFERENCE.replace('platform="highweb"', 'platform="other"'),
                     REFERENCE.replace("www.bbc.co.uk", "example.test"),
                     REFERENCE.replace("/mundo/", "/news/"),
                     REFERENCE.replace("</caption>", "</caption>Una negación externa.")):
            with self.subTest(text=text):
                self.assertIn("<link", " ".join(_article_parts(resource(f'<article><p>{escape(text)}</p></article>'))[0]))

    def test_inline_markup_and_quoted_context_are_preserved(self):
        for markup in (f'<p><strong>{escape(REFERENCE)}</strong></p>',
                       f'<blockquote><p>{escape(REFERENCE)}</p></blockquote>',
                       f'<h2><p>{escape(REFERENCE)}</p></h2>'):
            with self.subTest(markup=markup):
                sentences, _, _, _ = _article_parts(resource(f'<article>{markup}</article>'))
                self.assertIn("<link", " ".join(sentences))

    def test_other_hosts_other_bbc_sections_and_plain_text_are_unchanged(self):
        markup = f'<article><p>{escape(REFERENCE)}</p></article>'
        for url in ("https://example.test/mundo/noticias/control", "https://www.bbc.com/news/control",
                    "https://www.bbc.com.evil.test/mundo/noticias/control"):
            with self.subTest(url=url):
                self.assertIn("<link", " ".join(_article_parts(resource(markup, url))[0]))
        self.assertIn("<link", " ".join(_article_parts(resource(REFERENCE, content_type="text/plain"))[0]))


if __name__ == "__main__":
    unittest.main()
