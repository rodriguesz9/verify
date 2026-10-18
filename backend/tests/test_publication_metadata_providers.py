"""Explicit editorial metadata is publication context, never event evidence.

Parse.ly documents parsely-pub-date at
https://docs.parse.ly/installation-resources/parsely-integration/metadata/metatags/
These controls are synthetic and do not perform requests to that service.
"""
import unittest

import helpers
from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _publication_date
from app.services.source_corroboration import _prepare_sources


def resource(head="", body="", content_type="text/html"):
    markup = f"<html><head>{head}</head><body><article>{body}</article></body></html>"
    return FetchedResource(markup.encode(), content_type, "https://www.nasa.gov/missions/aurora-record/", "utf-8")


def metadata(value, key="parsely-pub-date"):
    return f'<meta name="{key}" content="{value}">'


class PublicationMetadataProviderTests(unittest.TestCase):
    def test_parsely_publication_uses_existing_calendar_timestamp_contract(self):
        for value in ("2021-08-12", "2021-08-12T09:00:00Z", "2021-08-12T09:00:00+00:00",
                      "2021-08-12T00:05:00+03:00", "2021-08-12T23:55:00-03:00",
                      "2021-08-12 09:00:00", "2021-08-12T09:00:00.123456Z"):
            with self.subTest(value=value):
                # Keep the stated civil date; no invented offset or UTC day.
                self.assertEqual(_publication_date(resource(metadata(value))), "2021-08-12")

    def test_provider_agreement_is_accepted_without_precedence_override(self):
        head = metadata("2021-08-12T09:00:00Z") + metadata("2021-08-12 14:32:00", "datePublished")
        head += '<meta property="article:published_time" content="2021-08-12T15:00:00+03:00">'
        self.assertEqual(_publication_date(resource(head)), "2021-08-12")
        self.assertEqual(_publication_date(resource(head + metadata("2021-08-12T09:00:00Z"))), "2021-08-12")

    def test_conflicting_publication_providers_or_duplicates_abstain(self):
        for other in (metadata("2021-08-13T09:00:00Z"), metadata("2021-08-13", "datePublished"),
                      '<meta property="article:published_time" content="2021-08-13T09:00:00Z">'):
            with self.subTest(other=other):
                self.assertIsNone(_publication_date(resource(metadata("2021-08-12T09:00:00Z") + other)))
                self.assertIsNone(_publication_date(resource(other + metadata("2021-08-12T09:00:00Z"))))

    def test_invalid_or_future_publication_is_not_replaced_by_valid_candidate(self):
        valid = '<meta property="article:published_time" content="2021-08-12T09:00:00Z">'
        for value in ("", "2021", "2021-02-29T09:00:00Z", "2021-08-12T25:00:00Z", "2021-08-12T09:00:00+25:00",
                      "2021-08-12 arbitrary", "August 12, 2021", "3000-08-12T09:00:00Z"):
            with self.subTest(value=value):
                self.assertIsNone(_publication_date(resource(metadata(value))))
                self.assertIsNone(_publication_date(resource(valid + metadata(value))))
        self.assertIsNone(_publication_date(resource(metadata("not-a-date"), '<div class="date">12 August 2021</div>')))

    def test_update_metadata_never_substitutes_or_overrides_publication(self):
        for key in ("dateModified", "dateCreated", "og:updated_time", "parsely-modified-date", "parsely-updated-date"):
            with self.subTest(key=key):
                update = metadata("2021-08-13T09:00:00Z", key)
                self.assertIsNone(_publication_date(resource(update)))
                self.assertEqual(_publication_date(resource(metadata("2021-08-12T09:00:00Z") + update)), "2021-08-12")

    def test_body_hidden_metadata_and_ordinary_year_are_not_publication(self):
        for body in (metadata("2021-08-12T09:00:00Z"), "<p>A pesquisa foi publicada em 2021.</p>",
                     '<p>12 August 2021</p>', '<div hidden>' + metadata("2021-08-12T09:00:00Z") + "</div>",
                     '<script>const publication = "2021-08-12T09:00:00Z";</script>'):
            with self.subTest(body=body):
                self.assertIsNone(_publication_date(resource(body=body)))
        self.assertIsNone(_publication_date(resource(metadata("2021-08-12T09:00:00Z"), content_type="text/plain")))

    def test_publication_does_not_supply_missing_body_day_or_year(self):
        claim = "A nave Aurora colidiu intencionalmente com o asteroide Estrela em 12 de agosto de 2021."
        for statement in ("A nave Aurora colidiu intencionalmente com o asteroide Estrela.",
                          "A nave Aurora colidiu intencionalmente com o asteroide Estrela em 12 de agosto.",
                          "A nave Aurora colidiu intencionalmente com o asteroide Estrela em agosto de 2021."):
            with self.subTest(statement=statement):
                captured = resource(metadata("2021-08-12T09:00:00Z"), f"<p>{statement}</p>")
                sentences, title, truncated, roles = _article_parts(captured)
                document = {"url": captured.final_url, "title": title, "sentences": sentences,
                            "sentence_roles": roles, "truncated": truncated,
                            "publication_date": _publication_date(captured), "retrieved_at": "2026-10-17T12:00:00Z"}
                self.assertEqual(document["publication_date"], "2021-08-12")
                self.assertEqual(_prepare_sources([document], [claim], None)[0], [])


if __name__ == "__main__":
    unittest.main()
