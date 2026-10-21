"""Offline boundary tests, synthetic records; not factual accuracy controls."""

from dataclasses import replace
import json
import unittest

from app.services.official_source_body import (
    COPOM_INDEX_LIMIT, COPOM_INDEX_URL, COPOM_MAX_BYTES, COPOM_REFERENCE_DATE_SEMANTICS,
    CopomRecordReference, OfficialSourceBodyError, copom_detail_url,
    decode_copom_body, select_copom_reference,
)
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _publication_date


REFERENCE = CopomRecordReference(321, "2040-05-11", "321ª reunião - Copom controla taxa")
BODY = "O Comitê decidiu reduzir a taxa de controle para 8,25% ao ano."


def response(rows, *, detail=False):
    return FetchedResource(json.dumps({"conteudo": rows}).encode(), "application/json",
                           copom_detail_url(REFERENCE) if detail else COPOM_INDEX_URL, "utf-8")


def index_row(**changes):
    return {"nro_reuniao": 321, "dataReferencia": "2040-05-11", "titulo": REFERENCE.title, **changes}


def detail_row(**changes):
    return {**index_row(), "textoComunicado": "<p>" + BODY + "</p>", **changes}


class OfficialSourceBodyTests(unittest.TestCase):
    def test_exact_reference_has_no_inferred_adjacent_date_or_current_fallback(self):
        page = response([index_row()])
        self.assertEqual(select_copom_reference(page, "2040-05-11"), REFERENCE)
        self.assertIsNone(select_copom_reference(page, "2040-05-10"))
        self.assertIsNone(select_copom_reference(page, "2040-05-12"))
        self.assertIsNone(select_copom_reference(response([]), "2040-05-11"))

    def test_literal_body_separate_from_reference_date_and_index_title(self):
        source = decode_copom_body(response([detail_row(titulo="Comunicado oficial")], detail=True), REFERENCE)
        self.assertEqual(source.reference_date, REFERENCE.reference_date)
        self.assertEqual(source.reference_date_semantics, COPOM_REFERENCE_DATE_SEMANTICS)
        self.assertEqual(source.resource.final_url, copom_detail_url(REFERENCE))
        self.assertEqual(source.record_kind, "bcb_copom_comunicado")
        self.assertEqual(source.official_record["record_reference_date"], "2040-05-11")
        self.assertEqual(source.official_record["record_id"], "321")
        self.assertEqual(source.official_record["record_url"], source.resource.final_url)
        self.assertEqual(source.official_record["discovery_url"], COPOM_INDEX_URL)
        self.assertNotIn(REFERENCE.reference_date, source.resource.data.decode())
        self.assertNotIn(REFERENCE.title, source.resource.data.decode())
        self.assertIsNone(_publication_date(source.resource))
        sentences, _, _, roles = _article_parts(source.resource)
        self.assertIn(BODY, sentences)
        self.assertEqual(roles[sentences.index(BODY)], "body")
        self.assertEqual(roles[sentences.index("Comunicado oficial")], "context")

    def test_original_hidden_script_caption_context_does_not_become_body(self):
        markup = ('<p hidden>Não é texto visível.</p><script>veredito=true</script>'
                  '<figcaption>Imagem não prova decisão.</figcaption><p>' + BODY + '</p>')
        source = decode_copom_body(response([detail_row(textoComunicado=markup)], detail=True), REFERENCE)
        sentences, _, _, roles = _article_parts(source.resource)
        self.assertNotIn("Não é texto visível.", sentences)
        self.assertFalse(any("veredito" in text for text in sentences))
        self.assertEqual(roles[sentences.index("Imagem não prova decisão.")], "context")
        self.assertEqual(roles[sentences.index(BODY)], "body")

    def test_title_markup_escaped_not_executed_or_accepted_as_body(self):
        title = '<script>fakeBody()</script> Controle'
        source = decode_copom_body(response([detail_row(titulo=title)], detail=True), REFERENCE)
        self.assertIn(b"&lt;script&gt;", source.resource.data)
        sentences, _, _, roles = _article_parts(source.resource)
        self.assertEqual(roles[sentences.index(title)], "context")

    def test_not_news_id_or_arbitrary_query(self):
        self.assertTrue(copom_detail_url(REFERENCE).endswith("nro_reuniao=321"))
        for bad in (True, "321", 0, 5001, -1, 3.2):
            with self.subTest(number=bad), self.assertRaises(OfficialSourceBodyError):
                copom_detail_url(replace(REFERENCE, meeting_number=bad))

    def test_index_and_detail_require_exact_origin_path_query_mime_and_size(self):
        index, detail = response([index_row()]), response([detail_row()], detail=True)
        for source, decode in ((index, lambda value: select_copom_reference(value, "2040-05-11")),
                               (detail, lambda value: decode_copom_body(value, REFERENCE))):
            for altered in (
                replace(source, final_url=source.final_url.replace("www.bcb.gov.br", "www.bcb.gov.br.evil.test")),
                replace(source, final_url=source.final_url.replace("https:", "http:")),
                replace(source, final_url=source.final_url + "&token=private"),
                replace(source, content_type="text/html"),
                replace(source, data=b""), replace(source, data=b" " * (COPOM_MAX_BYTES + 1)),
            ):
                with self.subTest(url=altered.final_url), self.assertRaises(OfficialSourceBodyError):
                    decode(altered)

    def test_index_validates_all_rows_even_if_first_matches(self):
        for row in (index_row(nro_reuniao=True), index_row(nro_reuniao=0), index_row(dataReferencia="2040-02-30"),
                    index_row(dataReferencia="2040-5-11"), index_row(titulo=""), index_row(extra="hidden")):
            with self.subTest(row=row), self.assertRaises(OfficialSourceBodyError):
                select_copom_reference(response([index_row(), row]), "2040-05-11")

    def test_index_duplicate_number_or_date_is_ambiguous(self):
        for other in (index_row(), index_row(nro_reuniao=322), index_row(dataReferencia="2040-05-12")):
            with self.assertRaises(OfficialSourceBodyError):
                select_copom_reference(response([index_row(), other]), "2040-05-11")

    def test_invalid_requested_dates_rejected(self):
        for stamp in (None, 20400511, "2040-5-11", "2040-02-30", "2040-05-11T00:00:00", "2040-05-11&x=1"):
            with self.subTest(date=stamp), self.assertRaises(OfficialSourceBodyError):
                select_copom_reference(response([]), stamp)

    def test_detail_must_bind_both_official_number_and_reference_date(self):
        for row in (detail_row(nro_reuniao=322), detail_row(dataReferencia="2040-05-12"),
                    detail_row(nro_reuniao="321"), detail_row(textoComunicado=""),
                    detail_row(textoComunicado=None), detail_row(titulo=""), detail_row(extra="ignored")):
            with self.subTest(row=row), self.assertRaises(OfficialSourceBodyError):
                decode_copom_body(response([row], detail=True), REFERENCE)
        for rows in ([], [detail_row(), detail_row()]):
            with self.assertRaises(OfficialSourceBodyError):
                decode_copom_body(response(rows, detail=True), REFERENCE)

    def test_malformed_json_schema_duplicates_and_large_indexes_rejected(self):
        base = response([])
        for data in (b"not JSON", b"{\"conteudo\":[],\"conteudo\":[]}", b"[]",
                     b'{"conteudo":{},"other":[]}', b'{"conteudo":null}', b"\xff",
                     json.dumps({"conteudo": [index_row()] * (COPOM_INDEX_LIMIT + 1)}).encode()):
            with self.subTest(data=data[:50]), self.assertRaises(OfficialSourceBodyError):
                select_copom_reference(replace(base, data=data), "2040-05-11")


if __name__ == "__main__":
    unittest.main()
