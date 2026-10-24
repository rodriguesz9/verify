"""Same-article publication metadata, never JSON-LD factual evidence."""
import json
import unittest

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _publication_date
from app.services.source_corroboration import _prepare_sources

URL = "https://www.bbc.com/news/synthetic-news"
TITLE = "A pesquisadora Zeta morreu"
STAMP = "2026-10-23T12:00:00+00:00"


def node(**values):
    return {"@context": "https://schema.org", "@type": "ReportageNewsArticle", "url": URL,
            "mainEntityOfPage": URL, "headline": TITLE, "datePublished": "2004-05-06T10:30:00Z", **values}


def resource(data, *, extra="", body=None):
    body = f"<h1>{TITLE}</h1><p>A pesquisadora Zeta morreu.</p>" if body is None else body
    script = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
    return FetchedResource(f"<html><head>{extra}{script}</head><body><article>{body}</article></body></html>".encode(),
                           "text/html", URL, "utf-8")


class ArticleJsonLdPublicationTests(unittest.TestCase):
    def test_same_visible_article_url_headline_and_published_date(self):
        for kind in ("Article", "NewsArticle", "ReportageNewsArticle", "AnalysisNewsArticle"):
            for identity in (URL, {"@id": URL}):
                with self.subTest(kind=kind, identity=identity):
                    self.assertEqual(_publication_date(resource(node(**{"@type": kind, "mainEntityOfPage": identity}))), "2004-05-06")

    def test_top_level_list_and_direct_graph_do_not_walk_related_or_nested_bodies(self):
        other = node(**{"@type": "VideoObject", "datePublished": "2000-01-01"})
        self.assertEqual(_publication_date(resource([other, node()])), "2004-05-06")
        self.assertEqual(_publication_date(resource({"@graph": [other, node()]})), "2004-05-06")
        self.assertIsNone(_publication_date(resource({"related": [node()]})))
        self.assertIsNone(_publication_date(resource({"articleBody": node()})))

    def test_other_page_headline_type_or_ambiguous_identity_never_lend_metadata(self):
        for values in ({"url": URL + "-other"}, {"mainEntityOfPage": URL + "-other"},
                       {"headline": "Outra notícia"}, {"@type": "VideoObject"},
                       {"@type": ["NewsArticle", "VideoObject"]}, {"@type": [{}]},
                       {"@type": {"name": "NewsArticle"}}, {"url": None, "mainEntityOfPage": None}):
            with self.subTest(values=values):
                self.assertIsNone(_publication_date(resource(node(**values))))
        self.assertIsNone(_publication_date(resource(node(), body=f"<h1 hidden>{TITLE}</h1>")))
        self.assertIsNone(_publication_date(resource(node(), body=f'<h1><span hidden>{TITLE}</span></h1>')))

    def test_conflicting_invalid_and_future_dates_abstain_instead_of_overriding(self):
        meta = '<meta property="article:published_time" content="2004-05-06">'
        self.assertEqual(_publication_date(resource(node(), extra=meta)), "2004-05-06")
        for value in ("2004-05-07", "2004-02-31", "3000-05-06", None, [], "2004-05-06T25:00:00Z"):
            with self.subTest(value=value):
                self.assertIsNone(_publication_date(resource(node(datePublished=value), extra=meta)))
        self.assertIsNone(_publication_date(resource([node(), node(datePublished="2004-05-07")])))

    def test_modified_created_jsonld_body_and_plain_script_are_not_publication(self):
        no_publication = node(dateModified="2004-05-07", dateCreated="2004-05-01")
        del no_publication["datePublished"]
        self.assertIsNone(_publication_date(resource(no_publication)))
        captured = resource(node(articleBody="A pesquisadora Zeta morreu em 6 de maio de 2004."))
        sentences, _, _, _ = _article_parts(captured)
        self.assertNotIn("A pesquisadora Zeta morreu em 6 de maio de 2004.", sentences)
        self.assertIn("A pesquisadora Zeta morreu.", sentences)

    def test_bounded_jsonld_cannot_be_executable_or_ambiguous(self):
        malformed = '<script type="application/ld+json">{"datePublished":bad}</script>'
        self.assertIsNone(_publication_date(resource({}, extra=malformed)))
        self.assertIsNone(_publication_date(resource({"@graph": [node()] * 17})))
        self.assertIsNone(_publication_date(resource(node(articleBody="x" * 66000))))
        duplicated = json.dumps(node()).replace('"datePublished":', '"datePublished":"2004-05-07", "datePublished":')
        self.assertIsNone(_publication_date(resource({}, extra='<script type="application/ld+json">' + duplicated + '</script>')))

    def test_metadata_without_relative_body_link_cannot_confirm_event_date(self):
        captured = resource(node())
        sentences, title, truncated, roles = _article_parts(captured)
        document = {"url": URL, "sentences": sentences, "sentence_roles": roles,
                    "title": title, "truncated": truncated, "retrieved_at": STAMP,
                    "publication_date": _publication_date(captured)}
        self.assertEqual(document["publication_date"], "2004-05-06")
        self.assertEqual(_prepare_sources([document], ["A pesquisadora Zeta morreu em 6 de maio de 2004."], None)[0], [])


if __name__ == "__main__":
    unittest.main()
