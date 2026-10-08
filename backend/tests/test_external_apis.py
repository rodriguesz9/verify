import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import FakeSession, ScalarResult, app, fake_report, fake_user, override_auth_and_db, valid_png
from app.models.history import Verification


class ExternalApisIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_check_url_normalizes_url_scrapes_page_and_persists_analysis(self):
        report = fake_report(source_url="https://example.com/news")
        pipeline_result = {
            "report": report,
            "metrics": {"text_ai_probability": 0.12, "earliest_known_date": None},
        }
        scraped = {
            "text": "This page has enough article text for the audit to run successfully.",
            "meta": {"title": "Example", "description": ""},
        }

        with (
            patch("app.api.check_url.verify_limit", new=AsyncMock()) as verify_limit,
            patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value=scraped)) as fetch_page_text,
            patch("app.api.check_url.run_pipeline", new=AsyncMock(return_value=pipeline_result)) as run_pipeline,
        ):
            response = self.client.post("/api/check-url", json={"url": "example.com/news"})

        self.assertEqual(response.status_code, 200)
        returned = response.json()
        self.assertEqual({key: returned[key] for key in report}, report)
        self.assertEqual(returned["content_type"], "url")
        self.assertEqual(returned["source_text"], scraped["text"])
        self.assertIsNotNone(datetime.fromisoformat(returned["analyzed_at"]).tzinfo)
        self.assertEqual(returned["pdf_export_status"], "unavailable")  # incomplete legacy fixture
        verify_limit.assert_awaited_once_with(self.user, self.db, "TEXTUAL")
        fetch_page_text.assert_awaited_once_with("https://example.com/news")
        run_pipeline.assert_awaited_once_with(text=scraped["text"], url="https://example.com/news")
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verification.source_url, "https://example.com/news")
        self.assertEqual(self.db.commits, 1)

    def test_check_url_rejects_pages_without_enough_content(self):
        with (
            patch("app.api.check_url.verify_limit", new=AsyncMock()),
            patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value={"text": "Too short", "meta": {}})),
            patch("app.api.check_url.run_pipeline", new=AsyncMock()) as run_pipeline,
        ):
            response = self.client.post("/api/check-url", json={"url": "https://example.com"})

        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())
        run_pipeline.assert_not_awaited()
        self.assertEqual(self.db.commits, 0)

    def test_upload_does_not_reuse_unversioned_other_user_cache(self):
        cached_report = fake_report(summary="Cached image analysis.")
        cached_verification = SimpleNamespace(id=uuid.uuid4(), raw_result=cached_report)
        cached_entry = SimpleNamespace(
            cached_verdict_id=cached_verification.id,
            expires_at=datetime.now(timezone.utc).replace(year=2099),
        )
        self.db.execute_results = [ScalarResult(cached_entry), ScalarResult(cached_verification)]

        with (
            patch("app.api.upload.verify_limit", new=AsyncMock()),
            patch("app.api.upload.analyze_media", new=AsyncMock(return_value=fake_report(summary="New report"))) as analyzer,
        ):
            response = self.client.post(
                "/api/upload",
                files={"file": ("sample.png", valid_png(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"], "New report")
        analyzer.assert_awaited_once()
        self.assertEqual(self.db.commits, 1)


if __name__ == "__main__":
    unittest.main()
