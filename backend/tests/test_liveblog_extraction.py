"""Read explicit update streams without merging facts or borrowing clock dates."""
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _article_reference_leads, _publication_date
from app.services.source_corroboration import document_selection_audit


def resource(markup):
    return FetchedResource(markup.encode(), "text/html", "https://www.bbc.com/news/control", "utf-8")


def entry(body, *, day="2024-03-04", label="4 March 2024", qualifier="", clock_attributes=""):
    return (f'<article><header>{qualifier}<time datetime="{day}T12:30:00Z" {clock_attributes}>'
            f'{label}</time></header>{body}</article>')


def stream(*entries, container='id="liveblog-body"'):
    return f'<main><div {container}>' + "".join(entries) + '</div></main>'


class LiveblogExtractionTests(unittest.TestCase):
    def test_all_dated_updates_remain_in_dom_order_instead_of_only_longest_entry(self):
        newest = "A equipe confirmou que a operação terminou."
        older = "A equipe ainda estava preparando a operação."
        markup = stream(entry(f'<p>{newest}</p>'), entry(f'<p>{older}</p><p>Mais contexto anterior.</p>',
                         day="2024-03-03", label="3 March 2024"))
        sentences, _, truncated, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["4 March 2024", newest, "3 March 2024", older, "Mais contexto anterior."])
        self.assertEqual(roles, ["context", "body", "context", "body", "body"])
        self.assertFalse(truncated)

    def test_entry_clocks_are_context_boundaries_not_joined_to_event_statements(self):
        first = "A missão Aurora I foi lançada"
        second = "em 3 de março de 2024."
        markup = stream(entry(f'<p>{first}</p>'), entry(f'<p>{second}</p>'))
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["4 March 2024", first, "4 March 2024", second])
        self.assertEqual(roles, ["context", "body", "context", "body"])
        self.assertNotIn(first + " " + second, sentences)
        document = {"url": "https://www.bbc.com/news/control", "sentences": sentences,
                    "sentence_roles": roles, "retrieved_at": "2024-03-05T12:00:00+00:00"}
        self.assertEqual(document_selection_audit(first + " " + second, [document])["eligible_family_count"], 0)

    def test_key_events_and_other_content_outside_validated_entries_remain_context(self):
        callout = "A missão Aurora I foi lançada em 3 de março de 2024."
        markup = stream(entry('<p>A equipe preparou a operação.</p>'),
                        '<div><p>' + callout + '</p></div>',
                        entry('<p>A equipe encerrou a operação.</p>'))
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertIn((callout, "context"), list(zip(sentences, roles)))
        self.assertEqual([text for text, role in zip(sentences, roles) if role == "body"],
                         ["A equipe preparou a operação.", "A equipe encerrou a operação."])
        document = {"url": "https://www.bbc.com/news/control", "sentences": sentences,
                    "sentence_roles": roles, "retrieved_at": "2024-03-05T12:00:00+00:00"}
        self.assertEqual(document_selection_audit(callout, [document])["eligible_family_count"], 0)

    def test_repeated_clock_headers_still_separate_negation_and_date_fragments(self):
        fragments = ("A equipe não confirmou", "que a operação terminou.", "em 3 de março de 2024.")
        markup = stream(*(entry(f'<p>{fragment}</p>') for fragment in fragments))
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(list(zip(sentences, roles)),
                         [pair for fragment in fragments for pair in (("4 March 2024", "context"), (fragment, "body"))])
        self.assertNotIn(" ".join(fragments), sentences)

    def test_body_uncertainty_negation_and_same_entry_continuation_are_preserved(self):
        markup = stream(entry('<p>A equipe não confirmou</p><p>que a operação poderia terminar hoje.</p>'),
                        entry('<p>O relatório afirma que a estimativa ainda pode mudar.</p>'))
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertIn(("A equipe não confirmou que a operação poderia terminar hoje.", "body"),
                      list(zip(sentences, roles)))
        self.assertIn(("O relatório afirma que a estimativa ainda pode mudar.", "body"),
                      list(zip(sentences, roles)))

    def test_initial_denial_and_per_entry_qualifiers_stay_context(self):
        markup = ('<article><h1>É falso que a operação tenha terminado:</h1>'
                  + stream(entry('<p>A operação terminou.</p>', qualifier="Relato não confirmado: "),
                           entry('<p>A equipe permaneceu no local.</p>')) + '</article>')
        sentences, _, _, roles = _article_parts(resource(markup))
        pairs = list(zip(sentences, roles))
        self.assertIn(("É falso que a operação tenha terminado:", "context"), pairs)
        self.assertIn(("Relato não confirmado: 4 March 2024", "context"), pairs)
        self.assertNotIn(("A operação terminou.", "body"), pairs)

    def test_ordinary_multiple_articles_keep_existing_largest_article_selection(self):
        markup = stream(entry('<p>Primeiro texto breve.</p>'),
                        entry('<p>Segundo texto maior com o contexto factual preservado.</p>'),
                        container='id="ordinary-news-list"')
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["Segundo texto maior com o contexto factual preservado."])
        self.assertEqual(roles, ["body"])

    def test_explicit_class_token_works_but_similar_container_names_do_not(self):
        for container, recognized in (('class="extra js-liveblog-body other"', True),
                                       ('id="liveblog-body-extra"', False),
                                       ('class="js-liveblog-body-extra"', False)):
            with self.subTest(container=container):
                markup = stream(entry('<p>Atualização breve.</p>'), entry('<p>Atualização anterior mais extensa.</p>'),
                                container=container)
                sentences, _, _, _ = _article_parts(resource(markup))
                self.assertEqual("Atualização breve." in sentences, recognized)

    def test_missing_hidden_empty_or_invalid_own_clock_does_not_merge_entries(self):
        first = entry('<p>Atualização breve.</p>')
        variants = (
            '<article><p>Atualização anterior mais extensa sem relógio.</p></article>',
            entry('<p>Atualização anterior mais extensa com relógio oculto.</p>', clock_attributes="hidden"),
            entry('<p>Atualização anterior mais extensa com relógio vazio.</p>', label=""),
            entry('<p>Atualização anterior mais extensa com relógio inválido.</p>', day="2024-02-31"),
            '<article><header><time datetime="2024-03-03T12:00:00Z" style="display:none">3 March 2024</time>'
            '</header><p>Atualização anterior mais extensa com relógio invisível.</p></article>',
        )
        for second in variants:
            with self.subTest(second=second):
                sentences, _, _, _ = _article_parts(resource(stream(first, second)))
                self.assertNotIn("Atualização breve.", sentences)

    def test_entry_time_properties_do_not_supply_whole_blog_publication_date(self):
        markup = stream(entry('<p>Um acontecimento foi relatado.</p>', clock_attributes='itemprop="datePublished"'),
                        entry('<p>Outro acontecimento foi relatado.</p>', clock_attributes='itemprop="datePublished"'))
        self.assertIsNone(_publication_date(resource(markup)))
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual([sentence for sentence, role in zip(sentences, roles) if role == "body"],
                         ["Um acontecimento foi relatado.", "Outro acontecimento foi relatado."])

    def test_global_explicit_publication_is_preserved_without_promoting_entry_dates(self):
        markup = ('<head><meta property="article:published_time" content="2024-03-01T09:00:00Z"></head>'
                  + stream(entry('<p>Uma operação foi concluída.</p>'),
                           entry('<p>Outra operação foi concluída.</p>', day="2024-03-03", label="3 March 2024")))
        self.assertEqual(_publication_date(resource(markup)), "2024-03-01")
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertTrue(all("March" not in sentence for sentence, role in zip(sentences, roles) if role == "body"))

    def test_same_50000_character_ceiling_discards_partial_final_statement(self):
        markup = stream(entry('<p>' + "x" * 51000 + ' condição ainda não resolvida.</p>'),
                        entry('<p>Atualização posterior fora do limite.</p>'))
        sentences, _, truncated, _ = _article_parts(resource(markup))
        self.assertTrue(truncated)
        self.assertNotIn("Atualização posterior fora do limite.", sentences)
        self.assertTrue(all("x" not in sentence for sentence in sentences))

    def test_primary_reference_discovery_reads_both_entries_without_using_header_links(self):
        first = entry('<p><a href="https://www.nasa.gov/reference-one/">Primeiro documento citado</a></p>')
        second = entry('<p><a href="https://www.who.int/reference-two/">Segundo documento citado</a></p>'
                       '<p>Contexto adicional torna este texto mais longo.</p>')
        first = first.replace('<header>', '<header><a href="https://www.nasa.gov/clock-link/">Relógio</a>')
        references = _article_reference_leads(resource(stream(first, second)))
        self.assertEqual([reference["link"] for reference in references],
                         ["https://www.nasa.gov/reference-one/", "https://www.who.int/reference-two/"])


if __name__ == "__main__":
    unittest.main()
