"""Institutional ficha links are reading leads, never original article evidence.

Two invented laws exercise identity, provenance and shared retrieval limits.
These offline controls do not measure remote retrieval or factual accuracy.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from app.core import pipeline
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import (
    _article_parts, _article_reference_leads, collect_source_attribution,
    primary_reference_leads,
)
from app.services.source_corroboration import _prepare_sources


FIXTURES = json.loads((Path(__file__).parent / "fixtures/validation/legislative-origin.json").read_text())["cases"]
FIRST = FIXTURES[0]
SOURCE, TARGET = FIRST["source_url"], FIRST["target_url"]
HEADING, HREF = FIRST["legal_heading"], FIRST["origin_href"]
CLAIM = "O artigo 1º da Lei nº 7.204, de 9 de abril de 1976, declarou aberto o arquivo Alfa."
KIND, METHOD = "legislative_original_publication", "legislative_original_reference"


def resource(markup=None, url=SOURCE):
    return FetchedResource((FIRST["html"] if markup is None else markup).encode(), "text/html", url, "utf-8")


def document(references, url=SOURCE, **fields):
    return {"url": url, "reference_leads": references, **fields}


def bridge_refs(page=None):
    return [row for row in _article_reference_leads(resource() if page is None else page)
            if row.get("reference_kind") == KIND]


def reference(target=TARGET, heading=HEADING):
    return {"link": target, "title": heading, "reference_kind": KIND}


class LegislativeOriginalReferenceTests(unittest.IsolatedAsyncioTestCase):
    def test_generic_number_date_period_and_record_not_known_law_table(self):
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture["id"]):
                page = resource(fixture["html"], fixture["source_url"])
                refs = bridge_refs(page)
                self.assertEqual(refs, [reference(fixture["target_url"], fixture["legal_heading"])])
                claim = "O artigo 1º da " + fixture["legal_heading"] + " declarou uma regra Alfa."
                self.assertEqual(primary_reference_leads(claim, [document(refs, fixture["source_url"])]), [{
                    "link": fixture["target_url"], "title": fixture["legal_heading"], "retrieval_method": METHOD,
                }])

    def test_absolute_or_relative_real_href_does_not_generate_destination(self):
        markup = FIRST["html"]
        self.assertEqual(bridge_refs(resource(markup.replace(HREF, TARGET))), [reference()])
        for absent in (markup.replace(f'href="{HREF}"', ""),
                       markup.replace(f'href="{HREF}"', 'data-href="' + HREF + '"'),
                       markup.replace(f'href="{HREF}"', 'href="#publication"')):
            with self.subTest(markup=absent):
                self.assertEqual(bridge_refs(resource(absent)), [])

    def test_source_target_and_heading_identity_and_record_must_all_match(self):
        destinations = [
            TARGET.replace("lei-7204-", "lei-7205-"),
            TARGET.replace("-9-abril-", "-10-abril-"),
            TARGET.replace("-abril-", "-maio-"),
            TARGET.replace("-1976-", "-1977-"),
            TARGET.replace("-812345-", "-812346-"),
            TARGET.replace("/1970-1979/", "/1960-1969/"),
            TARGET.replace("/lei/", "/leimp/"),
        ]
        for target in destinations:
            with self.subTest(target=target):
                self.assertEqual(bridge_refs(resource(FIRST["html"].replace(HREF, target))), [])
        for heading in (HEADING.replace("7.204", "7.205"), HEADING.replace("9 DE ABRIL", "10 DE ABRIL"),
                        HEADING.replace("1976", "1977"), HEADING.replace("9 DE ABRIL", "31 DE ABRIL")):
            self.assertEqual(bridge_refs(resource(FIRST["html"].replace(HEADING, heading))), [])
        self.assertEqual(bridge_refs(resource(url=SOURCE.replace("lei-7204-", "lei-7205-"))), [])

    def test_exact_origin_notice_and_unique_complete_visible_legal_heading(self):
        for label in ("Leia mais", "Publicação", "Não é Texto - Publicação Original",
                      "Texto - Publicação Original (apenas um exemplo)"):
            self.assertEqual(bridge_refs(resource(FIRST["html"].replace("Texto - Publicação Original", label))), [])
        for change in (
            FIRST["html"].replace(f"<h1>{HEADING}</h1>", ""),
            FIRST["html"].replace(f"<h1>{HEADING}</h1>", f'<meta name="law" content="{HEADING}">'),
            FIRST["html"].replace(f"<h1>{HEADING}</h1>", f"<h1>{HEADING}</h1><h1>{HEADING}</h1>"),
            FIRST["html"].replace("Lei Exemplo Alfa", "LEI Nº 7.205, DE 9 DE ABRIL DE 1976"),
            FIRST["html"].replace("Legislação Informatizada - Dados da Norma", "Lista de documentos"),
        ):
            with self.subTest(markup=change):
                self.assertEqual(bridge_refs(resource(change)), [])
        # A generic portal heading and a popular title do not add law identities.
        self.assertEqual(bridge_refs(resource("<h1>Legislação</h1>" + FIRST["html"])), [reference()])

    def test_two_origin_anchors_are_ambiguous_even_if_destinations_repeat(self):
        original = f'<a href="{HREF}"><strong>Texto - Publicação Original</strong></a>'
        for second in (original, original.replace("56789", "56790")):
            self.assertEqual(bridge_refs(resource(FIRST["html"].replace(original, original + second))), [])

    def test_hidden_navigation_ads_quotes_metadata_and_headers_do_not_supply_bridge(self):
        for wrapper in ('<nav>{}</nav>', '<header>{}</header>', '<footer>{}</footer>', '<aside>{}</aside>',
                        '<blockquote>{}</blockquote>', '<figcaption>{}</figcaption>', '<div hidden>{}</div>',
                        '<div aria-hidden="true">{}</div>', '<div role="navigation">{}</div>',
                        '<div style="display:none">{}</div>', '<div class="advertisement">{}</div>',
                        '<div class="related-card">{}</div>', '<template>{}</template>'):
            with self.subTest(wrapper=wrapper):
                self.assertEqual(bridge_refs(resource(wrapper.format(FIRST["html"]))), [])
        hidden_heading = FIRST["html"].replace(f"<h1>{HEADING}", f"<h1 hidden>{HEADING}")
        self.assertEqual(bridge_refs(resource(hidden_heading)), [])
        self.assertEqual(bridge_refs(resource(FIRST["html"].replace('<a href=', '<a rel="sponsored" href='))), [])

    def test_same_host_https_static_paths_only_no_query_fragment_credentials_or_ports(self):
        destinations = [TARGET.replace("www2.camara.leg.br", "www.camara.leg.br"),
                        TARGET.replace("www2.camara.leg.br", "www.senado.leg.br"),
                        TARGET.replace("www2.camara.leg.br", "www2.camara.leg.br.evil.test"),
                        TARGET.replace("https://", "http://"), TARGET + "?ref=index", TARGET + "#art1",
                        TARGET.replace("https://", "https://user:opaque@"),
                        TARGET.replace("www2.camara.leg.br", "www2.camara.leg.br:8443"),
                        TARGET.replace("www2.camara.leg.br", "127.0.0.1"),
                        TARGET.replace("lei-7204", "lei%2D7204"), "javascript:alert(1)", "https://[", SOURCE]
        for target in destinations:
            with self.subTest(target=target):
                self.assertEqual(bridge_refs(resource(FIRST["html"].replace(HREF, target))), [])
        for source in (SOURCE + "?ref=search", SOURCE + "#body", TARGET,
                       SOURCE.replace("www2.camara.leg.br", "unlisted.test")):
            self.assertEqual(bridge_refs(resource(url=source)), [])

    def test_selector_requires_complete_unique_matching_claim_reference(self):
        refs = [reference()]
        for claim in ("A Lei abriu o arquivo Alfa.", "A Lei 7.204 abriu o arquivo Alfa.",
                      "A norma de 9 de abril de 1976 abriu o arquivo Alfa.",
                      CLAIM.replace("7.204", "7.205"), CLAIM.replace("9 de abril", "10 de abril"),
                      CLAIM + " A Lei nº 7.205, de 9 de abril de 1976, também trata do assunto."):
            with self.subTest(claim=claim):
                self.assertEqual(primary_reference_leads(claim, [document(refs)]), [])

    def test_matching_complete_lowercase_identity_needs_no_capitalized_name(self):
        claim = "o artigo 1º da lei nº 7.204, de 9 de abril de 1976, declarou aberto o arquivo."
        self.assertEqual(primary_reference_leads(claim, [document([reference()])]), [{
            "link": TARGET, "title": HEADING, "retrieval_method": METHOD,
        }])

    def test_empty_query_and_fragment_delimiters_do_not_hide_in_canonicalization(self):
        for suffix in ("?", "#"):
            with self.subTest(suffix=suffix):
                self.assertEqual(bridge_refs(resource(FIRST["html"].replace(HREF, TARGET + suffix))), [])
                self.assertEqual(bridge_refs(resource(url=SOURCE + suffix)), [])
                self.assertEqual(primary_reference_leads(CLAIM, [document([reference(TARGET + suffix)])]), [])
                self.assertEqual(primary_reference_leads(CLAIM, [document([reference()], SOURCE + suffix)]), [])

    def test_selector_rechecks_identity_type_host_and_submitted_exclusions(self):
        for fields in ({"source_role": "submitted_source"}, {"url": TARGET},
                       {"url": SOURCE.replace("www2.camara.leg.br", "www.camara.leg.br")},
                       {"url": SOURCE.replace("812345", "812346")}):
            self.assertEqual(primary_reference_leads(CLAIM, [document([reference()], **fields)]), [])
        for forged in (reference(TARGET.replace("7204", "7205")), reference(TARGET + "#article"),
                       reference(heading=HEADING.replace("1976", "1977"))):
            self.assertEqual(primary_reference_leads(CLAIM, [document([forged])]), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document([reference()])], SOURCE), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document([reference()])], TARGET), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document([reference()])], excluded_urls=[TARGET]), [])

    def test_shared_two_reference_cap_is_not_expanded(self):
        ordinary = [{"link": f"https://www.nasa.gov/alfa-record-{index}/", "title": "Alfa record"} for index in range(3)]
        refs = [reference(), *ordinary]
        self.assertEqual(len(primary_reference_leads(CLAIM, [document(refs)])), 2)
        previously_followed = [{"link": "https://www.nasa.gov/alfa-record/", "title": "Alfa record",
                               "retrieval_method": "inline_cited_primary_reference"}]
        selected = pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None, {}, previously_followed)
        self.assertEqual(len(selected), 1)
        self.assertEqual(pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None, {}, previously_followed + selected), [])

    def test_attempts_redirect_aliases_and_followed_documents_do_not_recrawl(self):
        refs = [reference()]
        self.assertEqual(pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None,
                         {TARGET: {"failure": "timeout"}}, []), [])
        self.assertEqual(pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None,
                         {"https://www2.camara.leg.br/redirect": {"url": TARGET}}, []), [])
        followed = [{"link": SOURCE, "title": HEADING, "retrieval_method": METHOD}]
        self.assertEqual(pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None, {}, followed), [])

    async def test_index_ementa_heading_and_link_are_not_article_evidence_or_implicit_read(self):
        page = resource()
        sentences, _, _, roles = _article_parts(page)
        self.assertIn((HEADING, "context"), zip(sentences, roles))
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=page)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[{"link": SOURCE}], include_documents=True)
        fetch.assert_awaited_once()
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["_documents"][0]["reference_leads"], [reference()])
        selected, passages, _, _ = _prepare_sources(result["_documents"], [CLAIM], None)
        self.assertEqual(selected, [])
        self.assertEqual(passages, {})

    async def test_following_reference_charges_same_read_cap_and_does_not_refund_failure(self):
        selected = primary_reference_leads(CLAIM, [document([reference()])])
        self.assertEqual(len(selected), 1)
        cache = {}
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=HTTPException(403, "Offline control"))) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=selected,
                include_documents=True, fetched_cache=cache, max_sources=1)
            self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)
            await collect_source_attribution(CLAIM, [CLAIM], search_results=selected + [{"link": SOURCE}],
                include_documents=True, fetched_cache=cache, max_sources=1)
        fetch.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
