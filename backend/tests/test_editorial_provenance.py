"""Offline media-credit/textual-origin boundaries; no factual accuracy claim."""
import unittest
import json
import os
from unittest.mock import AsyncMock, patch

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _fetch_article
from app.services.source_corroboration import source_family, usable_source_families, select_comparison_documents, corroborate_sources

CLAIM = "A Rainha Elizabeth II morreu em 8 de setembro de 2022."


def resource(markup, url="https://www.bbc.com/story"):
    return FetchedResource(("<html><body><article>" + markup + "</article></body></html>").encode(),
                           "text/html", url, "utf-8")


def parsed(markup, url="https://www.bbc.com/story"):
    provenance = {}
    sentences, title, truncated, roles = _article_parts(resource(markup, url), provenance=provenance)
    return {"url": url, "title": title, "sentences": sentences, "sentence_roles": roles,
            "truncated": truncated, "retrieved_at": "2026-10-12T12:00:00+00:00",
            "editorial_provenance": provenance}


def family(document):
    return source_family(document["url"], " ".join(document["sentences"]),
                         provenance=document.get("editorial_provenance"))


class EditorialProvenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepared_textual_families_survive_final_assessment_without_raw_photo_rescan(self):
        async def answer(prompt, **kwargs):
            request = json.loads(prompt)
            return json.dumps({"claims": [{"claim_id": "c1", "source_reviews": [
                {"source_id": item["source_id"], "assessment": "evidence", "evidence": [
                    {"excerpt_id": item["passages"][0]["excerpt_id"], "relation": "supports"}]}
                for item in request["sources"]]}]})
        for textual_credit in (False, True):
            docs = [parsed('<figcaption>Foto: Jane Smith/Divulgação via Reuters</figcaption>'
                           + ('<div class="byline">Por Reuters</div>' if textual_credit else '')
                           + f'<p>{CLAIM}</p>', "https://www.bbc.com/story"),
                    parsed('<figcaption>© Reuters/John Smith/Direitos reservados</figcaption>'
                           + ('<div class="byline">Por Reuters</div>' if textual_credit else '')
                           + '<p>Em 8 de setembro de 2022, a Rainha Elizabeth II faleceu.</p>', "https://www.cnn.com/story")]
            with self.subTest(textual_credit=textual_credit), patch.dict(os.environ, {
                    "SOURCE_CROSSCHECK_ENABLED": "true", "SOURCE_CROSSCHECK_PRIMARY_PROVIDER": "gemini"}), \
                 patch("app.services.source_corroboration.gemini_client.generate_text", new=AsyncMock(side_effect=answer)) as model:
                result = await corroborate_sources(CLAIM, docs)
            if textual_credit:
                self.assertEqual(result["state"], "insufficient")
                model.assert_not_awaited()
            else:
                self.assertEqual(result["state"], "corroborated")
                self.assertEqual(set(result["claims"][0]["supporting_publishers"]), {"bbc", "cnn"})
                model.assert_awaited_once()

    def test_isolated_photo_credits_preserve_context_and_textual_families(self):
        first = parsed('<h1>Registro do evento</h1><div class="byline">Por Redação</div>'
            '<p class="content-media__description">Retrato da monarca — Foto: Jane Smith/Divulgação via Reuters</p>'
            f'<p>{CLAIM}</p>')
        second = parsed('<figure><figcaption>© Reuters/John Smith/Direitos reservados</figcaption></figure>'
            f'<p>Em 8 de setembro de 2022, a Rainha Elizabeth II morreu.</p>', "https://www.cnn.com/story")
        self.assertEqual(family(first), "bbc")
        self.assertEqual(family(second), "cnn")
        self.assertIn("Retrato da monarca — Foto: Jane Smith/Divulgação via Reuters", first["sentences"])
        self.assertEqual(first["sentence_roles"][2], "context")
        self.assertIn("© Reuters/John Smith/Direitos reservados", second["sentences"])
        self.assertEqual(usable_source_families(CLAIM, [first, second]), {"bbc", "cnn"})
        selected = select_comparison_documents(CLAIM, [first, second])
        self.assertEqual(selected, select_comparison_documents(CLAIM, selected))
        self.assertEqual(selected[0]["editorial_provenance"], first["editorial_provenance"])

    def test_photo_metadata_cannot_erase_separate_byline_or_textual_wire_credit(self):
        for credit in ('<div class="byline">Por Reuters</div>',
                       '<p>Segundo a Reuters, este registro foi publicado.</p>',
                       '<p>Republicação do texto. Fonte: Reuters</p>'):
            with self.subTest(credit=credit):
                doc = parsed('<figure><figcaption>© Reuters/John Smith/Direitos reservados</figcaption></figure>'
                             + credit + f'<p>{CLAIM}</p>')
                self.assertEqual(family(doc), "reuters")

    def test_mixed_photo_and_textual_origins_keep_actual_textual_agency(self):
        doc = parsed('<figure><figcaption>Foto: Jane Smith/Divulgação via Reuters</figcaption></figure>'
                     f'<div class="byline">Por Associated Press</div><p>{CLAIM}</p>')
        self.assertEqual(family(doc), "ap")
        # A separate explicit textual credit in the same unit stays visible.
        doc = parsed('<figcaption>Foto: Jane Smith via Reuters; texto por AFP</figcaption>' + f'<p>{CLAIM}</p>')
        self.assertEqual(doc["editorial_provenance"]["media_credit_fragments"], ["Foto: Jane Smith via Reuters"])
        self.assertEqual(family(doc), "afp")

    def test_word_photo_in_prose_or_in_authorship_cannot_hide_dependency(self):
        for markup in ('<p>A palavra Foto: introduz uma reportagem segundo a Reuters.</p>',
                       '<p>Foto: Jane Smith/Divulgação via Reuters</p>',
                       '<div class="byline">Foto: reportagem por Reuters</div>',
                       '<figcaption>Foto: reportagem por Reuters</figcaption>'):
            with self.subTest(markup=markup):
                doc = parsed(markup + f'<p>{CLAIM}</p>')
                self.assertEqual(doc["editorial_provenance"]["media_credit_fragments"], [])
                self.assertEqual(family(doc), "reuters")

    def test_missing_invalid_or_unmatched_provenance_falls_back_to_complete_body(self):
        body = "© Reuters/John Smith/Direitos reservados " + CLAIM
        invalid = [None, {}, {"version": "unknown", "media_credit_fragments": []},
                   {"version": "visible_media_credits_v1", "media_credit_fragments": ["Por Reuters"]},
                   {"version": "visible_media_credits_v1", "media_credit_fragments": ["Foto: Jane Smith via Reuters"]},
                   {"version": "visible_media_credits_v1", "media_credit_fragments": "all"},
                   {"version": "visible_media_credits_v1", "media_credit_fragments": [], "body": ""}]
        for provenance in invalid:
            with self.subTest(provenance=provenance):
                self.assertEqual(source_family("https://www.bbc.com/story", body, provenance=provenance), "reuters")

    def test_repeated_caption_fragment_cannot_erase_identical_textual_authorship(self):
        fragment = "Foto: Jane Smith/Divulgação via Reuters"
        docs = [parsed(f'<figcaption>{fragment}</figcaption><div class="byline">Texto e {fragment}</div>'
                       + f'<p>{CLAIM}</p>', url) for url in ("https://www.bbc.com/story", "https://www.cnn.com/story")]
        self.assertEqual({family(doc) for doc in docs}, {"reuters"})
        self.assertEqual(usable_source_families(CLAIM, docs), {"reuters"})

    def test_single_mixed_text_and_photo_caption_is_textual_dependency(self):
        for mixed in ("Texto e Foto: Jane Smith/Divulgação via Reuters",
                      "Reportagem e imagem: Jane Smith via Reuters",
                      "Text and photo: Jane Smith via Reuters"):
            for url in ("https://www.bbc.com/story", "https://www.cnn.com/story"):
                with self.subTest(mixed=mixed, url=url):
                    doc = parsed(f'<figcaption>{mixed}</figcaption><p>{CLAIM}</p>', url)
                    self.assertEqual(doc["editorial_provenance"]["media_credit_fragments"], [])
                    self.assertEqual(family(doc), "reuters")

    def test_ambiguous_repeated_media_credits_fail_closed_without_removing_context(self):
        fragment = "Foto: Jane Smith/Divulgação via Reuters"
        doc = parsed(f'<figcaption>{fragment}</figcaption><figcaption>{fragment}</figcaption><p>{CLAIM}</p>')
        self.assertEqual(family(doc), "reuters")
        self.assertEqual(" ".join(doc["sentences"]).count(fragment), 2)

    def test_hidden_or_unrelated_media_does_not_supply_photo_provenance(self):
        doc = parsed('<figure hidden><figcaption>Foto: Jane Smith via Reuters</figcaption></figure>'
                     '<div class="byline">Por Reuters</div>' + f'<p>{CLAIM}</p>')
        self.assertEqual(doc["editorial_provenance"]["media_credit_fragments"], [])
        self.assertEqual(family(doc), "reuters")

    async def test_fetched_document_keeps_internal_provenance(self):
        page = resource('<figcaption>© Reuters/John Smith/Direitos reservados</figcaption>' + f'<p>{CLAIM}</p>')
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=page)):
            doc = await _fetch_article(page.final_url)
        self.assertEqual(doc["editorial_provenance"], {"version": "visible_media_credits_v1",
            "media_credit_fragments": ["© Reuters/John Smith/Direitos reservados"]})
        self.assertEqual(family(doc), "bbc")
