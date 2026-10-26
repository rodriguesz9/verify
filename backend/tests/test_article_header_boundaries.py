"""Semantic header context cannot become a prefix of the first body subject."""
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts
from app.services.source_corroboration import source_family


DEFINITION = ("O Telescópio Espacial Aurora Boreal (também conhecido como ABST ou Aurora) "
              "é um instrumento destinado à observação do espaço.")


def read(html):
    sentences, _, _, roles = _article_parts(FetchedResource(
        html.encode(), "text/html", "https://www.bbc.com/test-public-source", "utf-8"))
    return list(zip(roles, sentences))


class ArticleHeaderBoundaryTests(unittest.TestCase):
    def test_unmarked_byline_and_ui_are_context_and_do_not_prefix_first_subject(self):
        rows = read("<article><header><h1>Observação do espaço</h1>"
                    "<h2>História do instrumento</h2><div><span>Nome da jornalista</span>"
                    "<div><a href='/seguir'>Adicionar publicação</a></div></div></header>"
                    f"<div><p>{DEFINITION}</p><p>O ABST foi lançado em 14 de março de 2020.</p></div></article>")
        self.assertIn(("context", "Nome da jornalista"), rows)
        self.assertIn(("context", "Adicionar publicação"), rows)
        self.assertIn(("context", "Observação do espaço"), rows)
        self.assertEqual([text for role, text in rows if role == "body"][0], DEFINITION)

    def test_nested_header_wrappers_preserve_heading_boundaries_without_flattening(self):
        rows = read("<article><header><div><h1>História do instrumento</h1>"
                    "<div><h2>Um subtítulo</h2><span>Nome da jornalista</span></div></div></header>"
                    f"<p>{DEFINITION}</p></article>")
        self.assertEqual(rows, [("context", "História do instrumento"), ("context", "Um subtítulo"),
                                ("context", "Nome da jornalista"), ("body", DEFINITION)])

    def test_unfinished_denial_remains_context_controlling_next_paragraph(self):
        rows = read("<article><header><div><h1>É falso que:</h1><span>Nome da jornalista</span>"
                    "</div></header><p>O objeto Zeta foi lançado em 14 de março de 2020.</p></article>")
        self.assertIn(("context", "É falso que:"), rows)
        self.assertIn(("context", "Nome da jornalista"), rows)
        self.assertIn(("context", "O objeto Zeta foi lançado em 14 de março de 2020."), rows)
        self.assertFalse(any(role == "body" for role, _ in rows))

    def test_wire_credit_is_preserved_in_dependency_context(self):
        rows = read("<article><header><h1>Observação do espaço</h1><div>Por Reuters</div>"
                    f"</header><div><p>{DEFINITION}</p></div></article>")
        self.assertIn(("context", "Por Reuters"), rows)
        self.assertEqual(source_family("https://www.bbc.com/test-public-source",
                                       " ".join(text for _, text in rows)), "reuters")

    def test_inline_quantities_and_words_are_not_split_into_new_values(self):
        rows = read("<article><header><h1>Descrição do objeto</h1><span>Nome da jornalista</span>"
                    "</header><p>O instrumento tem 1<strong>6</strong> sensores e uma lente.</p></article>")
        self.assertEqual([text for role, text in rows if role == "body"],
                         ["O instrumento tem 16 sensores e uma lente."])

    def test_explicit_article_body_inside_header_does_not_borrow_header_as_identity(self):
        rows = read("<article><header><h1>Nome de um instrumento</h1><div itemprop='articleBody'>"
                    "<p>Um instrumento foi lançado em 14 de março de 2020.</p></div>"
                    "</header><p>Texto relacionado fora do corpo explícito.</p></article>")
        self.assertIn(("context", "Nome de um instrumento"), rows)
        self.assertIn(("body", "Um instrumento foi lançado em 14 de março de 2020."), rows)
        self.assertIn(("context", "Texto relacionado fora do corpo explícito."), rows)
        self.assertFalse(any("Nome de um instrumento" in text for role, text in rows if role == "body"))

    def test_non_article_header_is_not_promoted_to_source_evidence(self):
        rows = read("<header><h1>É falso que:</h1><div>Nome da jornalista</div></header>"
                    "<article><p>O evento Zeta ocorreu em 2020.</p></article>")
        self.assertIn(("context", "É falso que:"), rows)
        self.assertFalse(any(role == "body" for role, _ in rows))
