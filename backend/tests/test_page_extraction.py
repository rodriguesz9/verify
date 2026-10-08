from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from app.api.check_url import fetch_page_text
from app.services.public_fetch import FetchedResource


class PageExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def extract(self, data, content_type="text/html", encoding="utf-8"):
        resource = FetchedResource(data, content_type, "https://example.test/final", encoding)
        with patch("app.api.check_url.fetch_public_resource", new=AsyncMock(return_value=resource)) as fetch:
            result = await fetch_page_text("https://example.test/control")
        self.assertEqual(fetch.await_args.kwargs["max_bytes"], 2 * 1024 * 1024)
        self.assertEqual(result["final_url"], resource.final_url)
        return result

    async def test_main_headline_negation_and_visible_values_are_preserved(self):
        data = (Path(__file__).parent / "fixtures/validation/links/pagina-controle.html").read_bytes()
        result = await self.extract(data)
        self.assertEqual(result["text"], "CONTROLE FICTÍCIO. Não pague uma taxa para liberar seu Pix. Valor informado: R$ 123,45. Data informada: 03/10/2026.")
        self.assertIn("Controle fictício", result["meta"]["title"])

    async def test_plain_text_is_not_interpreted_as_html(self):
        text = "Não remova <nao> nem <script> deste controle literal. Valor: R$ 123,45."
        result = await self.extract(text.encode(), "text/plain")
        self.assertEqual(result["text"], text)
        self.assertEqual(result["meta"], {"title": "", "description": ""})

    async def test_nested_hidden_elements_case_and_style_spacing(self):
        result = await self.extract(b'<article><header>Visible title</header><p hidden="false"><b>Hidden</b></p><p aria-hidden="TRUE">Hidden</p><p style="color: red; VISIBILITY : hidden !important;">Hidden</p><p>Visible body</p></article>')
        self.assertEqual(result["text"], "Visible title Visible body")

    async def test_fallback_body_and_unknown_encoding_remain_bounded(self):
        result = await self.extract(('<html><head><title>Metadata only</title></head><body><nav>Menu</nav><p>' + 'A' * 6000 + '</p></body></html>').encode(), encoding="not-a-codec")
        self.assertEqual(result["text"], 'A' * 5000)
        self.assertEqual(result["meta"]["title"], "Metadata only")

    async def test_hidden_article_does_not_override_visible_main(self):
        result = await self.extract(b'<main hidden>Hidden main</main><article>Visible article</article>')
        self.assertEqual(result["text"], "Visible article")
