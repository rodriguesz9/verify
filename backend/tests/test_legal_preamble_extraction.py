"""Normative DOM boundaries, not an exception for any particular diploma."""
import unittest

import helpers  # disables provider credentials and dotenv before imports
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts
from app.services.source_corroboration import document_selection_audit


TITLE = "LEI Nº 3.353, DE 13 DE MAIO DE 1888"
PREAMBLE = ("A Princeza Imperial Regente, em nome de Sua Majestade o Imperador, o Senhor D. "
            "Pedro II, Faz saber a todos os subditos do Imperio que a Assembléa Geral "
            "Decretou e Ella Sanccionou a Lei seguinte:")
FIRST = "Art. 1º É declarada extincta desde a data d'esta Lei, a escravidão no Brazil."
SECOND = "Art. 2º Revogam-se as disposições em contrário."
CLAIM = "O artigo 1º da Lei nº 3.353, de 13 de maio de 1888, não declarou legalmente extinta a escravidão no Brasil."


def extract(markup):
    resource = FetchedResource(markup.encode(), "text/html",
        "https://www2.camara.leg.br/legin/fed/ato-publicacaooriginal.html", "utf-8")
    sentences, title, truncated, roles = _article_parts(resource)
    return {"url": resource.final_url, "sentences": sentences, "sentence_roles": roles,
            "title": title, "truncated": truncated, "retrieved_at": "2026-10-16T12:00:00+00:00"}


class LegalPreambleExtractionTests(unittest.TestCase):
    def test_real_public_dom_preamble_and_br_do_not_swallow_article_identifier(self):
        # Reduced public-domain legislative DOM captured during UI validation:
        # preamble and article 1 share one <p>, separated only by <br>/<strong>.
        markup = f'<article><h1>{TITLE}</h1><p>{PREAMBLE}<br><br><strong>     </strong>{FIRST}</p><p>{SECOND}</p></article>'
        document = extract(markup)
        pairs = list(zip(document["sentences"], document["sentence_roles"]))
        self.assertIn((FIRST, "body"), pairs)
        self.assertIn((SECOND, "body"), pairs)
        self.assertTrue(all(role == "context" for sentence, role in pairs if "Faz saber" in sentence or "Pedro II" in sentence))
        self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 1)

    def test_generic_other_article_number_topic_diploma_does_not_require_known_case(self):
        title = "Lei nº 8.541, de 15 de abril de 2010"
        preamble = "A Câmara aprovou e a autoridade promulgou a Lei seguinte:"
        article = "Art. 7º É declarada extinta a taxa no Município Zeta."
        document = extract(f'<article><h1>{title}</h1><p>{preamble} {article}</p></article>')
        self.assertIn((article, "body"), list(zip(document["sentences"], document["sentence_roles"])))
        claim = "O artigo 7º da Lei nº 8.541, de 15 de abril de 2010, não declarou legalmente extinta a taxa no Município Zeta."
        self.assertEqual(document_selection_audit(claim, [document])["eligible_family_count"], 1)

    def test_denied_or_fabricated_preamble_cannot_lend_legal_identity(self):
        for prefix in ("É falso que ", "Não ocorreu o seguinte: ", "Reprodução hipotética: ", "Texto fabricado: "):
            with self.subTest(prefix=prefix):
                document = extract(f'<article><h1>{TITLE}</h1><p>{prefix}{PREAMBLE}<br>{FIRST}</p></article>')
                self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 0)

    def test_quoted_or_heading_preamble_does_not_promote_article_to_body(self):
        for tag in ("blockquote", "h2", "figcaption"):
            with self.subTest(tag=tag):
                document = extract(f'<article><h1>{TITLE}</h1><{tag}>{PREAMBLE} {FIRST}</{tag}></article>')
                self.assertNotIn((FIRST, "body"), list(zip(document["sentences"], document["sentence_roles"])))
                self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 0)

    def test_arbitrary_prose_before_art_marker_is_not_treated_as_normative_preamble(self):
        document = extract(f'<article><h1>{TITLE}</h1><p>Uma outra norma foi descrita assim: {FIRST}</p></article>')
        self.assertNotIn((FIRST, "body"), list(zip(document["sentences"], document["sentence_roles"])))
        self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 0)

    def test_article_two_never_borrows_article_one_payload(self):
        document = extract(f'<article><h1>{TITLE}</h1><p>{PREAMBLE}<br>{FIRST}</p><p>{SECOND}</p></article>')
        for wrong in (CLAIM.replace("artigo 1º", "artigo 2º"), CLAIM.replace("3.353", "3.354"),
                      CLAIM.replace("13 de maio", "14 de maio"), CLAIM.replace("escravidão", "propriedade")):
            with self.subTest(claim=wrong):
                self.assertEqual(document_selection_audit(wrong, [document])["eligible_family_count"], 0)

    def test_denial_in_heading_stays_attached_to_normative_text(self):
        document = extract(f'<article><h1>É falso que este seja o texto da {TITLE}:</h1><p>{PREAMBLE}<br>{FIRST}</p></article>')
        self.assertEqual(document_selection_audit(CLAIM, [document])["eligible_family_count"], 0)

    def test_split_preserves_original_punctuation_and_all_preamble_words(self):
        document = extract(f'<article><p>{PREAMBLE}<br>{FIRST}</p></article>')
        self.assertEqual(" ".join(document["sentences"]), PREAMBLE + " " + FIRST)
        self.assertEqual(document["sentences"][-1], FIRST)


if __name__ == "__main__":
    unittest.main()
