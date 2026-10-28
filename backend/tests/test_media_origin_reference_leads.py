"""Closed media-origin notices yield reading leads, never article evidence."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import (
    _article_parts, _article_reference_leads, collect_source_attribution, primary_reference_leads,
)
from app.services.source_corroboration import _prepare_sources
from app.core import pipeline


CLAIM = "The Aurora spacecraft was launched on August 12, 2021."
SOURCE = "https://www.bbc.com/science/media-901"
TARGET = "https://www.bbc.com/science/article-902"
TITLE = "Aurora spacecraft launch report"


def resource(markup, url=SOURCE):
    return FetchedResource(("<article>" + markup + "</article>").encode(), "text/html", url, "utf-8")


def notice(target=TARGET, prefix="Este vídeo foi publicado em", label=None):
    return f'<p><i>{prefix} </i><a href="{target}">{label or target}</a></p>'


def page(markup=None, title=TITLE):
    return resource(f"<header><h1>{title}</h1></header>" + (notice() if markup is None else markup))


def document(references, url=SOURCE, **fields):
    return {"url": url, "reference_leads": references, **fields}


class MediaOriginReferenceTests(unittest.IsolatedAsyncioTestCase):
    def test_single_visible_origin_notice_uses_h1_as_discovery_title_only(self):
        for phrase in ("Este vídeo foi publicado em", "Este áudio foi publicado no",
                       "This video was published in", "This audio was published on"):
            with self.subTest(phrase=phrase):
                references = _article_reference_leads(page(notice(prefix=phrase)))
                self.assertEqual(references, [{"link": TARGET, "title": TITLE,
                                               "reference_kind": "media_origin_article"}])
                selected = primary_reference_leads(CLAIM, [document(references)])
                self.assertEqual(selected, [{"link": TARGET, "title": TITLE,
                                             "retrieval_method": "media_origin_article_reference"}])

    def test_relative_href_and_same_family_different_host_are_supported(self):
        for target, label in (("/science/article-902", TARGET),
                              ("https://www.bbc.co.uk/science/article-902", None)):
            with self.subTest(target=target):
                references = _article_reference_leads(page(notice(target, label=label)))
                self.assertEqual(len(references), 1)
                self.assertEqual(len(primary_reference_leads(CLAIM, [document(references)])), 1)

    def test_other_curated_editorial_publishers_use_same_closed_rule(self):
        origin = "https://www.reuters.com/science/media-aurora"
        target = "https://www.reuters.com/science/report-aurora"
        references = _article_reference_leads(resource(f"<h1>{TITLE}</h1>" + notice(target), origin))
        self.assertEqual([item["link"] for item in primary_reference_leads(CLAIM, [document(references, origin)])], [target])

    def test_malformed_qualified_or_unrelated_origin_phrases_are_not_notices(self):
        variants = [notice(prefix="Este vídeo poderá ser publicado em"),
                    notice(prefix="Este vídeo não foi publicado em"),
                    notice(prefix="Leia também"), notice(prefix="Segundo a mensagem, este vídeo foi publicado em"),
                    notice().replace("</p>", " — esta é apenas uma hipótese.</p>"),
                    notice().replace("<i>", "<i>Example: "),
                    notice(label="Leia o artigo"), notice(label="https://["),
                    f'<p><a href="{TARGET}">{TARGET}</a> Este vídeo foi publicado em</p>']
        for markup in variants:
            with self.subTest(markup=markup):
                self.assertEqual(_article_reference_leads(page(markup)), [])

    def test_exactly_one_anchor_and_one_unambiguous_visible_h1_are_required(self):
        for markup in (notice() + "<h1>Another Aurora report</h1>",
                       notice().replace("</p>", '<a href="https://www.bbc.com/other/">Other</a></p>'),
                       notice().replace("</p>", '<a>Other</a></p>')):
            with self.subTest(markup=markup):
                self.assertEqual(_article_reference_leads(page(markup)), [])
        self.assertEqual(_article_reference_leads(resource(notice())), [])
        self.assertEqual(_article_reference_leads(page(title="Aurora")), [])
        self.assertEqual(_article_reference_leads(page(title="Aurora " * 50)), [])
        self.assertEqual(_article_reference_leads(page(notice() + '<h1 hidden>Other title</h1>')),
                         [{"link": TARGET, "title": TITLE, "reference_kind": "media_origin_article"}])

    def test_hidden_navigation_ads_quotes_and_media_ui_cannot_supply_notice(self):
        for wrapper in ('<nav>{}</nav>', '<header>{}</header>', '<aside>{}</aside>', '<footer>{}</footer>',
                        '<blockquote>{}</blockquote>', '<figcaption>{}</figcaption>', '<div hidden>{}</div>',
                        '<div aria-hidden="true">{}</div>', '<div style="display:none">{}</div>',
                        '<div role="navigation">{}</div>', '<div class="advertisement">{}</div>',
                        '<div class="sponsored-content">{}</div>', '<div class="related-card">{}</div>',
                        '<template>{}</template>', '<video>{}</video>'):
            with self.subTest(wrapper=wrapper):
                self.assertEqual(_article_reference_leads(page(wrapper.format(notice()))), [])
        self.assertEqual(_article_reference_leads(page(notice().replace('<a href=', '<a rel="sponsored" href='))), [])

    def test_heading_must_be_visible_not_metadata_or_an_ad(self):
        for heading in ('<h1 hidden>Aurora report</h1>', '<nav><h1>Aurora report</h1></nav>',
                        '<div class="advertisement"><h1>Aurora report</h1></div>',
                        '<title>Aurora report</title>', '<meta property="og:title" content="Aurora report">',
                        '<h1 style="visibility:hidden">Aurora report</h1>'):
            with self.subTest(heading=heading):
                self.assertEqual(_article_reference_leads(resource(heading + notice())), [])

    def test_external_primary_utility_media_and_unsafe_destinations_cannot_be_media_origin(self):
        invalid = ["https://www.reuters.com/science/article-902", "https://www.bbc.com/",
                   "http://www.bbc.com/science/article-902", "https://www.bbc.com/science/article-902?ref=video",
                   "https://www.bbc.com/science/article-902#body", "https://www.bbc.com/science/audio.mp3",
                   "https://www.bbc.com/videos/aurora", "https://www.bbc.com/science/media-902",
                   "https://www.bbc.com/contact/aurora", "https://127.0.0.1/article-902",
                   "https://www.bbc.com.evil.test/article-902", "https://user:secret@www.bbc.com/article-902",
                   "https://www.bbc.com:8443/article-902", "https://[", SOURCE]
        for target in invalid:
            with self.subTest(target=target):
                self.assertEqual(_article_reference_leads(page(notice(target))), [])
        # Ordinary primary citations retain their previous independent path;
        # this new kind cannot turn a primary source into an editorial origin.
        refs = _article_reference_leads(page(notice("https://www.nasa.gov/aurora-report/")))
        self.assertFalse(any(row.get("reference_kind") == "media_origin_article" for row in refs))
        for origin in ("https://unlisted.test/video", "https://www.nasa.gov/video"):
            self.assertEqual(_article_reference_leads(resource(f'<h1>{TITLE}</h1>' + notice(), origin)), [])

    def test_named_topic_is_required_in_visible_heading_and_never_repaired_by_slug(self):
        for title in ("A launch report", "Another spacecraft report", "Space mission August report"):
            with self.subTest(title=title):
                references = _article_reference_leads(page(notice("https://www.bbc.com/science/aurora"), title))
                self.assertTrue(references)
                self.assertEqual(primary_reference_leads(CLAIM, [document(references)]), [])

    def test_same_family_rules_are_rechecked_and_submitted_attempted_sources_excluded(self):
        refs = _article_reference_leads(page())
        for fields in ({"source_role": "submitted_source"}, {"url": "https://www.reuters.com/original"},
                       {"url": "https://unlisted.test/original"}, {"url": "https://www.nasa.gov/original"}):
            with self.subTest(fields=fields):
                self.assertEqual(primary_reference_leads(CLAIM, [document(refs, **fields)]), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(refs)], SOURCE), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(refs)], TARGET), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(refs)], excluded_urls=[TARGET]), [])
        for target in (SOURCE, TARGET + "#body", "https://www.bbc.com/video/aurora", "https://www.reuters.com/article"):
            forged = [{"link": target, "title": TITLE, "reference_kind": "media_origin_article"}]
            self.assertEqual(primary_reference_leads(CLAIM, [document(forged)]), [])

    def test_deduplication_caps_and_exclusion_before_cap_are_shared(self):
        targets = [f"https://www.bbc.com/science/aurora-report-{index}" for index in range(20)]
        refs = _article_reference_leads(page("".join(notice(target) for target in targets)))
        self.assertEqual(len(refs), 12)
        self.assertEqual([row["link"] for row in primary_reference_leads(CLAIM, [document(refs)])], targets[:2])
        self.assertEqual([row["link"] for row in primary_reference_leads(CLAIM, [document(refs)], excluded_urls=targets[:2])], targets[2:4])
        repeated = _article_reference_leads(page(notice() * 3))
        self.assertEqual(len(repeated), 1)

    def test_pipeline_excludes_attempted_urls_and_final_redirect_aliases_before_cap(self):
        alias, fresh = "https://www.bbc.com/science/alias-aurora", "https://www.bbc.com/science/fresh-aurora"
        refs = _article_reference_leads(page(notice() + notice(alias) + notice(fresh)))
        cache = {TARGET: {"failure": "timeout"}, "https://www.bbc.com/science/redirect": {"url": alias}}
        found = pipeline._unread_primary_reference_leads(CLAIM, [document(refs)], None, cache, [])
        self.assertEqual([row["link"] for row in found], [fresh])
        self.assertEqual(len(refs), 3)  # Source records remain unchanged.

    def test_pipeline_followed_reference_cannot_become_parent_and_total_cap_is_shared(self):
        alias, nested, fresh = ("https://www.bbc.com/science/alias-aurora",
                                "https://www.bbc.com/science/nested-aurora", "https://www.bbc.com/science/fresh-aurora")
        followed = primary_reference_leads(CLAIM, [document(_article_reference_leads(page()))])
        cached = {TARGET: {"url": alias}}
        nested_refs = [{"link": nested, "title": TITLE, "reference_kind": "media_origin_article"}]
        documents = [document(nested_refs, alias), document(_article_reference_leads(page(notice(fresh))))]
        found = pipeline._unread_primary_reference_leads(CLAIM, documents, None, cached, followed)
        self.assertEqual([row["link"] for row in found], [fresh])
        self.assertEqual(pipeline._unread_primary_reference_leads(CLAIM, documents, None, cached, followed + found), [])
        ordinary = [{"link": "https://www.nasa.gov/aurora-report/", "title": TITLE,
                     "retrieval_method": "inline_cited_primary_reference"}]
        self.assertEqual(len(pipeline._unread_primary_reference_leads(CLAIM, documents[1:], None, {}, ordinary)), 1)

    async def test_heading_and_origin_link_never_supply_fact_or_trigger_recursion(self):
        source = page(notice() + "<p>The article discusses a different subject.</p>", CLAIM)
        sentences, _, _, roles = _article_parts(source)
        self.assertIn((CLAIM, "context"), zip(sentences, roles))
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=source)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[{"link": SOURCE}], include_documents=True)
        fetch.assert_awaited_once()
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["_documents"][0]["reference_leads"][0]["link"], TARGET)
        selected, passages, _, _ = _prepare_sources(result["_documents"], [CLAIM], None)
        self.assertEqual(selected, [])
        self.assertEqual(passages, {})

    async def test_new_reference_method_uses_existing_shared_fetch_attempt_cap(self):
        selected = primary_reference_leads(CLAIM, [document(_article_reference_leads(page()))])
        leads = [{"link": "https://www.bbc.com/science/aurora-other", "title": TITLE}, *selected]
        body = resource("<p>The article discusses another subject.</p>", TARGET)
        cache = {}
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=body)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=leads,
                include_documents=True, fetched_cache=cache, max_sources=1)
            self.assertEqual(fetch.await_args.args[0], TARGET)
            self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 1)
            await collect_source_attribution(CLAIM, [CLAIM], search_results=[
                *leads, {"link": "https://www.bbc.com/science/aurora-third"}],
                include_documents=True, fetched_cache=cache, max_sources=1)
        fetch.assert_awaited_once()
