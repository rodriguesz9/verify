"""Editorial links are bounded retrieval hints, never body evidence or votes."""
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import (
    _article_parts, _article_reference_leads, collect_source_attribution, primary_reference_leads,
)


CLAIM = "The Aurora mission was launched on August 12, 2021."
TARGET = "https://science.nasa.gov/mission/aurora/launch/"


def resource(markup, url="https://www.bbc.com/science/original"):
    return FetchedResource(("<article>" + markup + "</article>").encode(), "text/html", url, "utf-8")


def callout(title="Aurora mission launch report", url=TARGET, *, action="Read the Story", kind="featured-story"):
    return (f'<div class="{kind}"><div><h2 class="story-title">{title}</h2></div>'
            f'<a href="{url}"><span>{action}</span></a></div>')


def document(references, **fields):
    return {"url": "https://www.bbc.com/science/original", "reference_leads": references, **fields}


class EditorialReferenceTests(unittest.IsolatedAsyncioTestCase):
    def test_story_action_uses_local_heading_only_as_a_retrieval_title(self):
        for kind, action in (("hds-featured-story", "Read the Story"),
                             ("editorial-callout", "Read full article"),
                             ("story-callout", "Leia a reportagem"),
                             ("article-callout", "Leia o artigo")):
            with self.subTest(kind=kind, action=action):
                references = _article_reference_leads(resource(callout(kind=kind, action=action)))
                self.assertEqual(references, [{"link": TARGET, "title": "Aurora mission launch report",
                                               "reference_kind": "editorial_callout"}])
                selected = primary_reference_leads(CLAIM, [document(references)])
                self.assertEqual(selected, [{"link": TARGET, "title": "Aurora mission launch report",
                                             "retrieval_method": "editorial_cited_primary_reference"}])

    def test_editorial_discovery_is_not_specific_to_an_institution_or_subject(self):
        target = "https://www.who.int/publications/i/item/lyra-study"
        references = _article_reference_leads(resource(callout("Lyra study results", target)))
        selected = primary_reference_leads("O estudo Lyra apresentou resultados em 12 de agosto de 2021.",
                                           [document(references)])
        self.assertEqual([item["link"] for item in selected], [target])

    def test_callout_requires_explicit_role_action_and_one_associated_preceding_heading(self):
        invalid = [
            callout(kind="ordinary-layout"),
            callout(action="Start now"),
            f'<div class="featured-story"><a href="{TARGET}">Read the Story</a></div>',
            f'<div class="featured-story"><a href="{TARGET}">Read the Story</a><h2>Aurora report</h2></div>',
            f'<div class="featured-story"><h2>Aurora report</h2><h3>Another report</h3><a href="{TARGET}">Read the Story</a></div>',
            f'<div class="featured-story"><h2>Aurora report</h2><a href="{TARGET}">Read the Story</a><a href="https://www.nasa.gov/other/">Other story</a></div>',
            f'<h2>Aurora report</h2><div class="featured-story"><a href="{TARGET}">Read the Story</a></div>',
            f'<div class="featured-story"><p><a href="{TARGET}">Read the Story</a></p></div>',
        ]
        for markup in invalid:
            with self.subTest(markup=markup):
                self.assertEqual(_article_reference_leads(resource(markup)), [])

    def test_navigation_ads_scripts_hidden_quotes_and_captions_cannot_supply_callouts(self):
        wrappers = [
            '<nav>{}</nav>', '<header>{}</header>', '<aside>{}</aside>', '<footer>{}</footer>',
            '<div role="navigation">{}</div>', '<div class="advertisement">{}</div>',
            '<div class="ad-container">{}</div>', '<div class="publicidade">{}</div>',
            '<div class="sponsored-content">{}</div>', '<script>{}</script>', '<template>{}</template>',
            '<blockquote>{}</blockquote>', '<figcaption>{}</figcaption>', '<div hidden>{}</div>',
            '<div aria-hidden="true">{}</div>', '<div style="display:none">{}</div>',
            '<div class="related-card">{}</div>',
        ]
        for wrapper in wrappers:
            with self.subTest(wrapper=wrapper):
                self.assertEqual(_article_reference_leads(resource(wrapper.format(callout()))), [])
        sponsored = callout().replace('<a href=', '<a rel="sponsored" href=')
        self.assertEqual(_article_reference_leads(resource(sponsored)), [])
        hidden_heading = callout().replace('<h2 class="story-title">', '<h2 hidden class="story-title">')
        self.assertEqual(_article_reference_leads(resource(hidden_heading)), [])

    def test_callout_topic_requires_named_identity_in_title_not_only_in_url(self):
        for title in ("Launch report", "Another telescope launch", "Mission December report", "Read the full article"):
            with self.subTest(title=title):
                references = _article_reference_leads(resource(callout(title)))
                self.assertTrue(references)  # The real anchor remains only a candidate.
                self.assertEqual(primary_reference_leads(CLAIM, [document(references)]), [])
        generic_claim = "The Mission was launched on December 25, 2021."
        references = _article_reference_leads(resource(callout("Mission December launch report")))
        self.assertEqual(primary_reference_leads(generic_claim, [document(references)]), [])

    def test_named_editorial_title_ranks_before_topic_present_only_in_inline_url(self):
        faq = "https://www.nasa.gov/aurora/faq/"
        markup = f'<p>See <a href="{faq}">Read more about the launch vehicle</a>.</p>' + callout()
        references = _article_reference_leads(resource(markup))
        self.assertEqual([item["link"] for item in references], [faq, TARGET])
        selected = primary_reference_leads(CLAIM, [document(references)])
        self.assertEqual([item["link"] for item in selected], [TARGET, faq])

    def test_callouts_preserve_primary_url_validation_and_submitted_source_exclusions(self):
        unsafe = ["javascript:alert(1)", "http://www.nasa.gov/aurora/", "https://127.0.0.1/aurora/",
                  "https://www.nasa.gov.evil.test/aurora/", "https://user:secret@www.nasa.gov/aurora/",
                  "https://www.nasa.gov:8443/aurora/", "https://www.nasa.gov/aurora/?key=opaque",
                  "https://www.nasa.gov/", "#section", "https://www.bbc.com/aurora/"]
        for target in unsafe:
            with self.subTest(target=target):
                self.assertEqual(_article_reference_leads(resource(callout(url=target))), [])
        references = _article_reference_leads(resource(callout()))
        self.assertEqual(primary_reference_leads(CLAIM, [document(references, source_role="submitted_source")]), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(references)], TARGET), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(references)], document([])["url"]), [])
        self.assertEqual(primary_reference_leads(CLAIM, [document(references, url="https://unlisted.example.test/a")]), [])

    def test_callouts_and_inline_citations_share_deduplication_and_existing_caps(self):
        references = _article_reference_leads(resource(callout() * 20))
        self.assertEqual(len(references), 1)
        many = "".join(callout(f"Aurora science report {index}", f"https://www.nasa.gov/aurora/{index}/")
                       for index in range(30))
        references = _article_reference_leads(resource(many))
        self.assertEqual(len(references), 12)
        self.assertEqual(len(primary_reference_leads(CLAIM, [document(references)])), 2)
        filler = '<p><a href="https://unlisted.example.test/article/">Unlisted</a></p>' * 200
        self.assertEqual(_article_reference_leads(resource(filler + callout())), [])
        inline = f'<p>See <a href="{TARGET}">Aurora launch</a>.</p>'
        references = _article_reference_leads(resource(inline + callout()))
        self.assertEqual(references, [{"link": TARGET, "title": "Aurora launch"}])

    async def test_title_and_action_never_supply_evidence_or_trigger_implicit_fetch(self):
        page = resource(callout(CLAIM) + '<p>The article body covers a different subject.</p>')
        sentences, _, _, roles = _article_parts(page)
        self.assertIn((CLAIM, "context"), zip(sentences, roles))
        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(return_value=page)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=[{"link": page.final_url}],
                                                      include_documents=True)
        fetch.assert_awaited_once()
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["_documents"][0]["reference_leads"][0]["link"], TARGET)
        self.assertNotIn("reference_leads", json.dumps({key: value for key, value in result.items() if key != "_documents"}))

    async def test_editorial_priority_uses_existing_fetch_budget_and_charges_failures(self):
        old = [f"https://www.bbc.com/old-{index}/" for index in range(3)]
        cache = {url: {"failure": "timeout"} for url in old}
        selected = primary_reference_leads(CLAIM, [document(_article_reference_leads(resource(callout())))])
        leads = [{"link": "https://www.nasa.gov/another-aurora/", "title": "Aurora launch"},
                 {"link": "https://www.cnnbrasil.com.br/aurora/", "title": "Aurora launch"}, *selected,
                 *[{"link": url} for url in old]]

        async def answer(url, **_kwargs):
            if url == TARGET:
                raise HTTPException(403, "Offline blocked control")
            return resource("<p>An unrelated body appears in this source.</p>", url)

        with patch("app.services.source_attribution.fetch_public_resource", new=AsyncMock(side_effect=answer)) as fetch:
            result = await collect_source_attribution(CLAIM, [CLAIM], search_results=leads,
                include_documents=True, fetched_cache=cache, max_sources=6)
            self.assertEqual(fetch.await_args_list[0].args[0], TARGET)
            self.assertEqual(result["coverage"]["cumulative_fetch_attempt_count"], 6)
            self.assertEqual(cache[TARGET], {"failure": "blocked_or_unavailable"})
            await collect_source_attribution(CLAIM, [CLAIM], search_results=[*leads,
                {"link": "https://www.who.int/aurora/", "title": "Aurora report",
                 "retrieval_method": "editorial_cited_primary_reference"}],
                include_documents=True, fetched_cache=cache, max_sources=6)
        self.assertEqual(fetch.await_count, 3)


if __name__ == "__main__":
    unittest.main()
