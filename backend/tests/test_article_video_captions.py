"""Structural player-caption controls, not topic-specific factual exceptions."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.public_fetch import FetchedResource
from app.services.source_attribution import _article_parts, _article_reference_leads, collect_source_attribution


FACT = "O instituto registrou crescimento de 2,8% em 2023 em relação a 2022."
CAPTION = "O cenário internacional pode comprometer a recuperação da economia"


def resource(markup, content_type="text/html"):
    return FetchedResource(markup.encode(), content_type, "https://example.test/article", "utf-8")


def player(caption=CAPTION, *, player_attributes='class="cxm-block-video"',
           caption_classes="codex-caption codex-caption--small", extra=""):
    return (f'<div {player_attributes}><div class="cxm-block-video__container">'
            f'<div class="cxm-block-video__caption-container">'
            f'<p class="{caption_classes}">{caption}</p>{extra}</div></div></div>')


class ArticleVideoCaptionTests(unittest.TestCase):
    def test_player_caption_without_final_period_cannot_merge_with_factual_paragraph(self):
        markup = f'<article>{player()}<p>{FACT}</p></article>'
        sentences, _, truncated, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [FACT])
        self.assertEqual(roles, ["body"])
        self.assertFalse(truncated)
        self.assertNotIn(CAPTION, " ".join(sentences))

    def test_exact_class_tokens_and_semantic_player_allow_extra_classes_and_order(self):
        for attributes in ('class="content-media cxm-block-video mc-column"',
                           'itemscope itemtype="https://schema.org/VideoObject"',
                           'itemscope itemtype="http://schema.org/VideoObject/"'):
            with self.subTest(attributes=attributes):
                markup = f'<article>{player(player_attributes=attributes, caption_classes="extra codex-caption--small codex-caption")}<p>{FACT}</p></article>'
                sentences, _, _, roles = _article_parts(resource(markup))
                self.assertEqual(sentences, [FACT])
                self.assertEqual(roles, ["body"])

    def test_only_caption_is_removed_not_factual_siblings_or_player_container(self):
        qualified = "A estimativa pode mudar e não constitui um resultado definitivo."
        markup = f'<article>{player(extra=f"<p>{qualified}</p>")}<p>{FACT}</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [qualified, FACT])
        self.assertEqual(roles, ["body", "body"])

    def test_same_caption_classes_outside_dedicated_player_container_are_preserved(self):
        for markup in (
            f'<p class="codex-caption codex-caption--small">{CAPTION}.</p>',
            f'<div class="cxm-block-video"><p class="codex-caption codex-caption--small">{CAPTION}.</p></div>',
            f'<div class="cxm-block-video__caption-container"><p class="codex-caption codex-caption--small">{CAPTION}.</p></div>',
        ):
            with self.subTest(markup=markup):
                sentences, _, _, _ = _article_parts(resource(f'<article>{markup}<p>{FACT}</p></article>'))
                self.assertIn(CAPTION + ".", sentences)
                self.assertIn(FACT, sentences)

    def test_similar_class_names_and_non_video_itemtypes_do_not_remove_prose(self):
        for markup in (
            player(player_attributes='class="cxm-block-video-preview"'),
            player(player_attributes='itemtype="https://schema.org/Article"'),
            player().replace('class="cxm-block-video__caption-container"', 'class="cxm-block-video__caption-container-extra"'),
            player(caption_classes="codex-caption-extra codex-caption--small"),
        ):
            with self.subTest(markup=markup):
                sentences, _, _, _ = _article_parts(resource(f'<article>{markup}</article>'))
                self.assertIn(CAPTION, " ".join(sentences))

    def test_inline_caption_words_and_qualifiers_in_real_paragraph_remain_literal(self):
        qualified = "O instituto informou que a produção pode crescer, mas não confirmou a previsão."
        markup = ('<article><div class="cxm-block-video"><div class="cxm-block-video__caption-container">'
                  '<p>O instituto informou que a produção <span class="codex-caption codex-caption--small">'
                  'pode crescer, mas não confirmou</span> a previsão.</p></div></div></article>')
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [qualified])
        self.assertEqual(roles, ["body"])

    def test_nested_caption_markup_cannot_erase_qualifier_from_enclosing_paragraph(self):
        markup = f'<article><p>O instituto não confirmou a previsão: {player(CAPTION + ".")}</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, ["O instituto não confirmou a previsão: " + CAPTION + "."])
        self.assertEqual(roles, ["body"])

    def test_quoted_heading_and_existing_caption_context_is_not_promoted_or_deleted(self):
        for tag in ("blockquote", "h2", "figcaption"):
            with self.subTest(tag=tag):
                markup = f'<article><{tag}>{player(CAPTION + ".")}</{tag}><p>{FACT}</p></article>'
                sentences, _, _, roles = _article_parts(resource(markup))
                self.assertIn((CAPTION + ".", "context"), list(zip(sentences, roles)))
                self.assertIn((FACT, "body"), list(zip(sentences, roles)))
        known_caption = f'<article><p class="media-caption">{CAPTION}.</p><p>{FACT}</p></article>'
        sentences, _, _, roles = _article_parts(resource(known_caption))
        self.assertEqual(list(zip(sentences, roles)), [(CAPTION + ".", "context"), (FACT, "body")])

    def test_body_uncertainty_and_negation_before_and_after_player_are_preserved(self):
        before = "O instituto não confirmou que a estimativa fosse definitiva."
        after = "A projeção pode mudar e depende de revisão metodológica."
        markup = f'<article><p>{before}</p>{player()}<p>{after}</p><p>{FACT}</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [before, after, FACT])
        self.assertEqual(roles, ["body", "body", "body"])

    def test_caption_only_article_cannot_displace_real_body_during_root_selection(self):
        markup = f'<article>{player(CAPTION * 30)}</article><article><p>{FACT}</p></article>'
        sentences, _, _, roles = _article_parts(resource(markup))
        self.assertEqual(sentences, [FACT])
        self.assertEqual(roles, ["body"])

    def test_player_caption_links_are_not_discovered_as_article_references(self):
        caption_link = '<a href="https://www.nasa.gov/player-only-reference/">Player reference</a>'
        body_link = '<p><a href="https://www.nasa.gov/ordinary-body-reference/">Ordinary article reference</a></p>'
        references = _article_reference_leads(resource(f'<article>{player(caption_link)}{body_link}</article>'))
        self.assertEqual(references, [{"link": "https://www.nasa.gov/ordinary-body-reference/",
                                      "title": "Ordinary article reference"}])

    def test_plain_text_is_not_interpreted_as_player_markup(self):
        text = player() + " " + FACT
        sentences, _, _, roles = _article_parts(resource(text, content_type="text/plain"))
        self.assertEqual(" ".join(sentences), text)
        self.assertEqual(roles, ["body"] * len(sentences))


class ArticleVideoCaptionAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def test_removed_caption_cannot_be_matched_as_body_evidence(self):
        caption = "O instituto anunciou crescimento de 8,2% em 2023 em relação a 2022."
        markup = f'<article>{player(caption)}<p>{FACT}</p></article>'
        for claim, expected in ((caption, "no_results"), (FACT, "found")):
            with self.subTest(claim=claim), patch(
                    "app.services.source_attribution.fetch_public_resource",
                    new=AsyncMock(return_value=resource(markup))):
                result = await collect_source_attribution(claim, [claim],
                    search_results=[{"link": "https://example.test/article"}], include_documents=True)
            self.assertEqual(result["status"], expected)
            self.assertEqual([match["excerpt"] for match in result["matches"]], [FACT] if claim == FACT else [])
            self.assertEqual(result["_documents"][0]["sentences"], [FACT])
            self.assertEqual(result["_documents"][0]["sentence_roles"], ["body"])


if __name__ == "__main__":
    unittest.main()
