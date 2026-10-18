"""Offline DOM-boundary controls; source repetition is not an accuracy result."""
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts
from app.services.source_corroboration import select_comparison_documents


EBC_BODY = (
    "Em 5 de outubro de 1988 foi promulgada a nova Constituição do Brasil, "
    "também chamada de Constituição Cidadã."
)
# Relevant visible DOM copied from the captured public EBC page, preserving
# its nested divs, explicit author group and distinct publication/event dates.
# Capture: source-body-v2-251.html, qa-context-verdicts-oct16.YeCcp8.
# Original: https://agenciabrasil.ebc.com.br/es/node/1336203
EBC_CAPTURE_FRAGMENT = """<div class="container-noticia rel-position bottomplayer-list" id="panel">
  <div id="node-1336203" class="node node-radioagencia">
    <div class="header-noticia full-width">
      <a href="/radioagencia-nacional/es/politica" class="editoria">Política</a>
      <h1 class="titulo-materia">
        História Hoje: Há 27 anos era promulgada a Constituição Cidadã      </h1>
      <div class="linha-fina-noticia"></div>
      <div class="rowflex noticia-play-btns">
        <a class="btn-download-audio"><div class="icon-download"></div><span>Baixar</span></a>
        <button class="btn-download-audio bottomplayer-item"><span>Tocar</span></button>
      </div>
    </div>
    <div class="subheader">
      <div class="container-autoria">
        <div class="autor-noticia">
            Apresentação Carmen Lúcia        </div>
        <div class="container-data rowflex">
          <div class="data">  05/10/2015 - 07:30</div>
          <!-- <div class="separador">|</div>
          <div class="hora">00:00</div> -->
        </div>
        <div class="local">  Brasília</div>
      </div>
      <nav class="compartilhamento rowflex"></nav>
    </div>
    <div class="capa-materia rel-position" href="#"></div>
    <div class="conteudo-noticia">
      <p>Em 5 de outubro de 1988 foi promulgada a nova Constituição do Brasil, também chamada de Constituição Cidadã.</p>
      <p> </p>
      <p>A lei fundamental e suprema do país, surgiu como uma resposta às reivindicações da sociedade por mudanças estruturais após 20 anos de governos militares.</p>
    </div>
  </div>
</div>"""


def extracted_document(markup):
    resource = FetchedResource(markup.encode(), "text/html", "https://www.bbc.com/test-record", "utf-8")
    sentences, title, truncated, roles = _article_parts(resource)
    return {"url": resource.final_url, "title": title, "sentences": sentences,
            "sentence_roles": roles, "truncated": truncated,
            "retrieved_at": "2026-10-01T12:00:00+00:00"}


class BylineBoundaryTests(unittest.TestCase):
    def test_captured_ebc_author_group_stays_context_and_body_date_stays_literal(self):
        document = extracted_document(EBC_CAPTURE_FRAGMENT)
        pairs = list(zip(document["sentences"], document["sentence_roles"]))
        self.assertIn((EBC_BODY, "body"), pairs)
        metadata = [(sentence, role) for sentence, role in pairs if "Carmen Lúcia" in sentence]
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0][1], "context")
        self.assertIn("05/10/2015 - 07:30", metadata[0][0])
        self.assertIn("Brasília", metadata[0][0])
        self.assertNotIn("1988", metadata[0][0])
        self.assertEqual(select_comparison_documents(EBC_BODY, [document]), [document])
        self.assertFalse(document["truncated"])

    def test_nested_metadata_boundaries_do_not_depend_on_event_or_publication_date(self):
        for container, marker, published, event in (
            ("div", 'class="container-autoria"', "17/03/2019 - 09:20", "12 de agosto de 1972"),
            ("section", 'class="byline"', "2008-11-21 15:42", "3 de janeiro de 1999"),
            ("header", 'itemprop="author"', "24 October 2023 08:15", "7 de maio de 2001"),
            ("address", 'class="author-credit"', "02/02/2010 - 14:00", "19 de abril de 1985"),
        ):
            with self.subTest(container=container, published=published, event=event):
                body = f"A estação Aurora foi inaugurada em {event}."
                markup = (f'<article><{container}><div {marker}><span>Reportagem Marina Costa</span> '
                          f'<div>{published}</div><div>Recife</div></div></{container}>'
                          f'<p>{body}</p></article>')
                document = extracted_document(markup)
                self.assertIn((body, "body"), zip(document["sentences"], document["sentence_roles"]))
                metadata = [(sentence, role) for sentence, role in zip(
                    document["sentences"], document["sentence_roles"]) if "Marina Costa" in sentence]
                self.assertEqual(len(metadata), 1)
                self.assertEqual(metadata[0][1], "context")
                self.assertIn(published, metadata[0][0])
                self.assertEqual(select_comparison_documents(body, [document]), [document])

    def test_author_and_date_in_narrative_are_preserved_without_metadata_markup(self):
        body = ("Em 05/10/2015, a autora Carmen Lúcia apresentou o programa sobre a "
                "Constituição promulgada em 5 de outubro de 1988.")
        document = extracted_document(
            '<article><div><section><p>Em <time datetime="2015-10-05">05/10/2015</time>, '
            'a autora <span itemprop="author">Carmen Lúcia</span> apresentou o programa sobre a '
            'Constituição promulgada em 5 de outubro de 1988.</p></section></div></article>')
        self.assertEqual(document["sentences"], [body])
        self.assertEqual(document["sentence_roles"], ["body"])
        self.assertEqual(select_comparison_documents(EBC_BODY, [document]), [])

    def test_explicit_byline_cannot_supply_evidence_even_when_it_contains_whole_claim(self):
        markup = (f'<article><div><div class="byline">{EBC_BODY}</div></div>'
                  '<p>Outra descrição ocupa o corpo da página.</p></article>')
        document = extracted_document(markup)
        self.assertIn((EBC_BODY, "context"), zip(document["sentences"], document["sentence_roles"]))
        self.assertEqual(select_comparison_documents(EBC_BODY, [document]), [])

    def test_nested_title_or_caption_cannot_supply_body_evidence(self):
        for marker in ('<div class="headline">{}</div>', '<h1>{}</h1>', '<figcaption>{}</figcaption>'):
            with self.subTest(marker=marker):
                markup = ('<article><div><section>' + marker.format(EBC_BODY)
                          + '</section></div><p>Outra descrição ocupa o corpo da página.</p></article>')
                document = extracted_document(markup)
                self.assertIn((EBC_BODY, "context"), zip(document["sentences"], document["sentence_roles"]))
                self.assertEqual(select_comparison_documents(EBC_BODY, [document]), [])

    def test_nested_correction_counterfeit_and_unfinished_denial_remain_qualifiers(self):
        for qualifier in ("Na verdade, o trecho abaixo contém uma data incorreta.",
                          "Sátira: reprodução fictícia de uma notícia histórica.", "É falso que:"):
            with self.subTest(qualifier=qualifier):
                markup = (f'<article><div><div class="subtitle">{qualifier}</div></div>'
                          f'<p>{EBC_BODY}</p></article>')
                document = extracted_document(markup)
                self.assertIn((qualifier, "context"), zip(document["sentences"], document["sentence_roles"]))
                self.assertIn(EBC_BODY, document["sentences"])
                self.assertEqual(select_comparison_documents(EBC_BODY, [document]), [])

    def test_flow_traversal_preserves_inline_number_and_word_boundaries(self):
        body = "A estação Aurora transportou 16 pessoas em 12 de agosto de 2001."
        markup = ('<article><div><section><p>A estação <em>Aurora</em> transportou '
                  '1<strong>6</strong> pessoas em 12 de agosto de 2001.</p></section></div></article>')
        document = extracted_document(markup)
        self.assertEqual(document["sentences"], [body])
        self.assertEqual(document["sentence_roles"], ["body"])


if __name__ == "__main__":
    unittest.main()
