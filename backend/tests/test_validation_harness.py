import unittest
import httpx
from unittest.mock import AsyncMock
from fastapi import HTTPException
from scripts.validation_ui_server import request_provider, local_page_control_fetch, LOCAL_PAGE_CONTROL_URL


class ValidationHarnessTests(unittest.TestCase):
    def test_pinned_public_fixture_preserves_https_host_and_sni(self):
        request = httpx.Request("GET", "https://8.8.8.8/", headers={"Host": "www.nasa.gov"},
                                extensions={"sni_hostname": "www.nasa.gov"})
        self.assertEqual(request_provider(request), "public_fetch")
        for url, host, sni in (("https://127.0.0.1/", "www.nasa.gov", "www.nasa.gov"),
                               ("http://8.8.8.8/", "www.nasa.gov", "www.nasa.gov"),
                               ("https://8.8.8.8/", "evil.test", "www.nasa.gov"),
                               ("https://8.8.8.8/", "www.nasa.gov", "evil.test"),
                               ("https://8.8.8.8:8443/", "www.nasa.gov", "www.nasa.gov")):
            self.assertIsNone(request_provider(httpx.Request("GET", url, headers={"Host": host}, extensions={"sni_hostname": sni})))
        self.assertIsNone(request_provider(httpx.Request("GET", "https://evil.test/")))


class LocalPageHarnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_explicit_test_url_is_simulated(self):
        original = AsyncMock(return_value="normal SSRF guard")
        fetch = local_page_control_fetch(original)
        resource = await fetch(LOCAL_PAGE_CONTROL_URL, max_bytes=2 * 1024 * 1024, allowed_types={"text/html"})
        self.assertEqual(resource.final_url, LOCAL_PAGE_CONTROL_URL)
        self.assertIn("Não pague".encode(), resource.data)
        original.assert_not_awaited()
        self.assertEqual(await fetch("http://127.0.0.1/health", max_bytes=100), "normal SSRF guard")
        original.assert_awaited_once_with("http://127.0.0.1/health", max_bytes=100)

    async def test_local_simulation_keeps_size_and_content_type_limits(self):
        fetch = local_page_control_fetch(AsyncMock())
        for kwargs, code in (({"max_bytes": 1, "allowed_types": {"text/html"}}, 413),
                             ({"max_bytes": 20000, "allowed_types": {"image/png"}}, 415)):
            with self.assertRaises(HTTPException) as caught:
                await fetch(LOCAL_PAGE_CONTROL_URL, **kwargs)
            self.assertEqual(caught.exception.status_code, code)
