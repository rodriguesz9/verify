"""URL persistence boundaries, offline only. Not a real-site accuracy test."""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from helpers import app, fake_user, FakeSession, override_auth_and_db
from app.api.check_url import normalize_analysis_url
from app.models.history import Verification
from app.models.schemas import MAX_ANALYSIS_URL_LENGTH, UrlRequest
from app.services.claim_policy import text_report
from app.services.pdf_snapshot import verify_pdf_snapshot


PAGE_TEXT = "Controle fictício: não pague R$ 123,45 em 07/10/2026. Não comprova precisão."


def url_at_length(length):
    prefix = "https://example.test/"
    return prefix + "x" * (length - len(prefix) - 6) + "FINAL1"


class UrlSchemaLimitTests(unittest.TestCase):
    def test_schema_matches_existing_database_column(self):
        self.assertEqual(MAX_ANALYSIS_URL_LENGTH, Verification.__table__.c.source_url.type.length)
        self.assertEqual(UrlRequest.model_json_schema()["properties"]["url"]["maxLength"], 512)

    def test_exact_boundary_is_kept_and_long_input_is_rejected_not_sliced(self):
        original = url_at_length(512)
        self.assertEqual(UrlRequest(url=original).url, original)
        with self.assertRaises(ValidationError):
            UrlRequest(url=url_at_length(513))
        with self.assertRaises(ValidationError):
            UrlRequest(url="x" * 4096)

    def test_surrounding_whitespace_is_trimmed_before_validation(self):
        original = url_at_length(512)
        self.assertEqual(UrlRequest(url="  " + original + "\n").url, original)
        for value in ("    ", " abcd ", None, 123):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                UrlRequest(url=value)

    def test_protocol_counts_toward_limit_and_case_does_not_duplicate_it(self):
        bare = url_at_length(512).removeprefix("https://")
        self.assertEqual(normalize_analysis_url(bare), "https://" + bare)
        with self.assertRaises(HTTPException) as caught:
            normalize_analysis_url(bare + "x")
        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("512", caught.exception.detail)
        uppercase = url_at_length(512).replace("https://", "HTTPS://", 1)
        self.assertEqual(normalize_analysis_url(uppercase), uppercase)


class UrlEndpointLimitTests(unittest.TestCase):
    def setUp(self):
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def send(self, value, final_url):
        with patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value={
                "text": PAGE_TEXT, "final_url": final_url,
                "extraction_details": {"method": "static_html", "truncated": False, "rendered_browser": False},
            })) as fetch, \
             patch("app.api.check_url.run_pipeline", new=AsyncMock(return_value={
                "report": text_report(PAGE_TEXT, []),
                "metrics": {"text_ai_probability": None, "earliest_known_date": None},
            })) as pipeline, \
             patch("app.api.check_url.verify_limit", new=AsyncMock()) as quota:
            response = self.client.post("/api/check-url", json={"url": value})
        return response, fetch, pipeline, quota

    def test_exact_boundary_persists_and_snapshot_preserves_full_address(self):
        value = url_at_length(512)
        response, fetch, pipeline, _ = self.send(value, value)
        self.assertEqual(response.status_code, 200)
        fetch.assert_awaited_once_with(value)
        pipeline.assert_awaited_once_with(text=PAGE_TEXT, url=value)
        self.assertEqual(self.db.commits, 1)
        stored = next(row for row in self.db.added if isinstance(row, Verification))
        self.assertEqual(stored.source_url, value)
        snapshot = verify_pdf_snapshot(response.json()["pdf_snapshot_token"], self.user)
        self.assertEqual(snapshot["source_url"], value)
        self.assertEqual(snapshot["query_input"], value)
        self.assertTrue(snapshot["source_url"].endswith("FINAL1"))
        self.assertNotIn("pdf_snapshot_token", stored.raw_result)

    def test_schema_oversize_rejected_before_fetch_provider_and_quota(self):
        response, fetch, pipeline, quota = self.send(url_at_length(513), "https://example.test/short")
        self.assertEqual(response.status_code, 422)
        fetch.assert_not_awaited()
        pipeline.assert_not_awaited()
        quota.assert_not_awaited()
        self.assertEqual(self.db.added, [])
        self.assertEqual(self.db.commits, 0)

    def test_added_protocol_cannot_overflow_persistence_bound(self):
        value = url_at_length(513).removeprefix("https://")
        response, fetch, pipeline, quota = self.send(value, "https://example.test/short")
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], str)
        self.assertIn("512", response.json()["detail"])
        fetch.assert_not_awaited()
        pipeline.assert_not_awaited()
        quota.assert_not_awaited()
        self.assertEqual(self.db.added, [])

    def test_redirected_oversize_rejected_before_provider_and_database(self):
        response, fetch, pipeline, quota = self.send("https://example.test/short", url_at_length(513))
        self.assertEqual(response.status_code, 422)
        self.assertIn("endereço final", response.json()["detail"])
        self.assertIn("nenhum endereço foi cortado", response.json()["detail"])
        fetch.assert_awaited_once()
        quota.assert_awaited_once()
        pipeline.assert_not_awaited()
        self.assertEqual(self.db.added, [])
        self.assertEqual(self.db.commits, 0)

    def test_redirected_exact_boundary_kept_with_distinct_original(self):
        original = "https://example.test/short"
        final_url = url_at_length(512)
        response, _, pipeline, _ = self.send(original, final_url)
        self.assertEqual(response.status_code, 200)
        pipeline.assert_awaited_once_with(text=PAGE_TEXT, url=final_url)
        report = verify_pdf_snapshot(response.json()["pdf_snapshot_token"], self.user)
        self.assertEqual(report["query_input"], original)
        self.assertEqual(report["source_url"], final_url)
        self.assertEqual(self.db.added[0].source_url, final_url)

    def test_percent_encoding_expansion_cannot_overflow_final_url(self):
        original = "https://example.test/" + "é" * 100
        encoded = "https://example.test/" + "%C3%A9" * 100
        response, _, pipeline, _ = self.send(original, encoded)
        self.assertEqual(response.status_code, 422)
        pipeline.assert_not_awaited()
        self.assertEqual(self.db.added, [])

    def test_anonymous_requests_obey_same_final_url_bound(self):
        override_auth_and_db(None, self.db)
        response, _, pipeline, _ = self.send("https://example.test/short", url_at_length(513))
        self.assertEqual(response.status_code, 422)
        pipeline.assert_not_awaited()
        self.assertEqual(self.db.commits, 0)


if __name__ == "__main__":
    unittest.main()
