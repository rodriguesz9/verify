"""Image attribution stays visible but cannot change a BODY sentence's subject."""
import unittest
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts

BODY = "A pesquisadora Zeta morreu em 6 de maio de 2004."


def parse(markup):
    return _article_parts(FetchedResource(markup.encode(), "text/html", "https://www.bbc.com/news/control", "utf-8"))


class StructuralVisualCreditTests(unittest.TestCase):
    def test_styled_credit_inside_explicit_media_unit_stays_separate_context(self):
        for label in ("Agência Aurora", "BBC", "Pessoa Zeta"):
            with self.subTest(label=label):
                markup = '<article><div data-testid="hero-image"><span class="Image-styles__CreditStyled-sc-abc-2">'
                markup += label + '</span></div><p>' + BODY + '</p></article>'
                sentences, _, _, roles = parse(markup)
                self.assertEqual(sentences, [label, BODY])
                self.assertEqual(roles, ["context", "body"])

    def test_visual_credit_cannot_become_a_fact_even_if_it_looks_like_a_sentence(self):
        markup = '<article><div data-testid="hero-image"><span class="Image-styles__CreditStyled-sc-a-1">'
        markup += BODY + '</span></div><p>Outra informação permanece no corpo.</p></article>'
        sentences, _, _, roles = parse(markup)
        self.assertEqual(roles[sentences.index(BODY)], "context")

    def test_style_or_publisher_word_alone_does_not_erase_ordinary_prose(self):
        markup = '<article><p><span class="Image-styles__CreditStyled-sc-a-1">BBC: </span>' + BODY + '</p></article>'
        sentences, _, _, roles = parse(markup)
        self.assertEqual(sentences, ["BBC: " + BODY])
        self.assertEqual(roles, ["body"])

    def test_figure_caption_and_subsequent_body_are_never_joined(self):
        sentences, _, _, roles = parse('<article><figure><span class="Figure-styles__CreditStyled-sc-z">Aurora</span>'
                                      '</figure><p>' + BODY + '</p></article>')
        self.assertEqual(sentences, ["Aurora", BODY])
        self.assertEqual(roles, ["context", "body"])


if __name__ == "__main__":
    unittest.main()
