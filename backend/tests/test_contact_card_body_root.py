"""Offline DOM-root boundaries. Contact cards never turn into factual votes."""
import unittest

from bs4 import BeautifulSoup

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _body_root
from app.services.source_corroboration import usable_source_families


FACT = "O Instituto Zeta divulgou o relatório anual em 15 de abril de 2010."
EXPLANATION = (
    "O documento reúne a descrição dos trabalhos desenvolvidos pelas equipes regionais durante o período analisado. "
    "A apresentação está organizada em capítulos e inclui a descrição de cada etapa do processo administrativo."
)
DETAILS = (
    "A leitura reúne as observações da equipe responsável e apresenta o caminho de acesso aos registros originais. "
    "Os documentos complementares estão organizados por assunto e acompanham as informações do registro principal."
)
CONTACT = ('<article class="card card--nolink" id="contact"><h3>Media contacts</h3>'
           '<p>Press Office: <a href="mailto:press@example.test">Contact team</a></p></article>')


def prose(first=FACT, identifier="prose"):
    return f'<div id="{identifier}"><p>{first}</p><p>{EXPLANATION}</p><p>{DETAILS}</p></div>'


def page(content, *, outside="", main_tag="main"):
    return f'<html><body>{outside}<{main_tag}><h1>Registro institucional</h1>{content}</{main_tag}></body></html>'


def parsed(markup, url="https://www.bbc.com/example"):
    resource = FetchedResource(markup.encode(), "text/html", url, "utf-8")
    sentences, title, truncated, roles = _article_parts(resource)
    return {"url": url, "title": title, "sentences": sentences, "sentence_roles": roles,
            "truncated": truncated, "retrieved_at": "2026-10-23T12:00:00+00:00"}


def body(document):
    return [sentence for sentence, role in zip(document["sentences"], document["sentence_roles"]) if role == "body"]


class ContactCardBodyRootTests(unittest.TestCase):
    def test_unique_substantial_prose_beats_only_utility_article_without_deleting_context(self):
        markup = page(prose() + CONTACT)
        root, scope = _body_root(BeautifulSoup(markup, "html.parser"))
        self.assertEqual(root["id"], "prose")
        self.assertEqual(scope.name, "main")
        result = parsed(markup)
        self.assertIn(FACT, body(result))
        self.assertIn("Media contacts", result["sentences"])
        self.assertNotIn("Media contacts", body(result))
        self.assertEqual(usable_source_families(FACT, [result]), {"bbc"})
        # More pages from the same family still do not become independent votes.
        self.assertEqual(usable_source_families(FACT, [result, parsed(markup, "https://www.bbc.com/other")]), {"bbc"})

    def test_semantic_main_role_works_without_main_tag_or_provider_specific_css(self):
        markup = '<html><body><section role="main"><h1>Registro</h1>' + prose() + CONTACT + '</section></body></html>'
        root, scope = _body_root(BeautifulSoup(markup, "html.parser"))
        self.assertEqual(root["id"], "prose")
        self.assertEqual(scope["role"], "main")
        self.assertIn(FACT, body(parsed(markup)))

    def test_captured_institutional_sentence_stays_original_body_not_a_rewritten_claim(self):
        # Public Europe-page wording captured during QA. No date is inferred
        # from a heading, no clause/date is stripped, and this is not a new
        # factual-accuracy measurement or an independent second source.
        quote = ("This led WHO to declare a Public Health Emergency of International Concern (PHEIC) "
                 "on 30 January 2020 and to characterize the outbreak as a pandemic on 11 March 2020.")
        markup = '<html><body><section role="main"><h1>Coronavirus disease (COVID-19) pandemic</h1>'
        markup += prose(first=quote) + CONTACT + '</section></body></html>'
        result = parsed(markup, "https://www.who.int/europe/emergencies/situations/covid-19")
        self.assertIn(quote, body(result))
        self.assertTrue(any("30 January 2020" in item and "11 March 2020" in item for item in body(result)))

    def test_article_with_h1_time_or_articlebody_keeps_existing_priority(self):
        for marker in ('<h1>Contacts</h1>', '<p><time datetime="2010-04-15">15 April 2010</time></p>',
                       '<div itemprop="articleBody"><p>Original body has explicit semantic priority.</p></div>'):
            with self.subTest(marker=marker):
                contact = CONTACT.replace('</article>', marker + '</article>')
                root, _scope = _body_root(BeautifulSoup(page(prose() + contact), "html.parser"))
                self.assertNotEqual(root.get("id"), "prose")
                self.assertNotIn(FACT, body(parsed(page(prose() + contact))))

    def test_news_cards_and_external_link_card_do_not_open_page_aggregation(self):
        news = '<article class="card" id="news"><h2>Notícia relacionada</h2><p>Outro acontecimento independente.</p></article>'
        for cards in (news + CONTACT, CONTACT.replace('mailto:press@example.test', 'https://example.test/story'),
                      CONTACT.replace('Media contacts', 'Related stories')):
            with self.subTest(cards=cards):
                root, _scope = _body_root(BeautifulSoup(page(prose() + cards), "html.parser"))
                self.assertNotEqual(root.get("id"), "prose")
                self.assertNotIn(FACT, body(parsed(page(prose() + cards))))

    def test_two_substantial_bodies_or_two_main_landmarks_are_ambiguous(self):
        alternatives = (page(prose() + prose(identifier="other-prose") + CONTACT),
                        '<html><body><main>' + prose() + CONTACT + '</main><section role="main">'
                        + prose(identifier="other-prose") + '</section></body></html>')
        for markup in alternatives:
            with self.subTest(markup=markup):
                root, _scope = _body_root(BeautifulSoup(markup, "html.parser"))
                self.assertEqual(root["id"], "contact")
                self.assertNotIn(FACT, body(parsed(markup)))

    def test_no_semantic_main_no_contact_link_and_short_prose_do_not_guess(self):
        alternatives = (page(prose() + CONTACT, main_tag="div"),
                        page(prose() + CONTACT.replace('href="mailto:press@example.test"', '')),
                        page('<div id="prose"><p>Short text.</p><p>Second short text.</p><p>Third short text.</p></div>' + CONTACT))
        for markup in alternatives:
            with self.subTest(markup=markup):
                root, _scope = _body_root(BeautifulSoup(markup, "html.parser"))
                self.assertEqual(root["id"], "contact")

    def test_titles_captions_and_navigation_never_supply_body_evidence(self):
        unrelated = prose(first="Este registro apenas descreve a organização das atividades da equipe local.")
        markup = page(f'<nav><p>{FACT}</p></nav><h2>{FACT}</h2><figcaption>{FACT}</figcaption>' + unrelated + CONTACT)
        result = parsed(markup)
        self.assertIn(FACT, result["sentences"])
        self.assertNotIn(FACT, body(result))
        self.assertFalse(usable_source_families(FACT, [result]))

    def test_contextual_prose_wrappers_are_not_promoted(self):
        for wrapper in ('<blockquote>{}</blockquote>', '<figcaption>{}</figcaption>', '<table><tr><td>{}</td></tr></table>',
                        '<div class="card">{}</div>', '<div class="subtitle">{}</div>'):
            with self.subTest(wrapper=wrapper):
                markup = page(wrapper.format(prose()) + CONTACT)
                root, _scope = _body_root(BeautifulSoup(markup, "html.parser"))
                self.assertEqual(root["id"], "contact")
                self.assertNotIn(FACT, body(parsed(markup)))

    def test_fiction_heading_is_kept_and_rejects_literal_claim(self):
        markup = page(prose() + CONTACT).replace('<h1>Registro institucional</h1>', '<h1>Fictional example</h1>')
        result = parsed(markup)
        self.assertIn("Fictional example", result["sentences"])
        self.assertIn(FACT, body(result))
        self.assertFalse(usable_source_families(FACT, [result]))

    def test_external_qualifier_and_unfinished_denial_keep_full_scope(self):
        for qualifier in ('<h1>Fictional example</h1>', '<p>É falso que:</p>'):
            with self.subTest(qualifier=qualifier):
                result = parsed(page(prose() + CONTACT, outside=qualifier))
                self.assertTrue(any("Fictional" in s or "É falso" in s for s in result["sentences"]))
                self.assertFalse(usable_source_families(FACT, [result]))


if __name__ == "__main__":
    unittest.main()
