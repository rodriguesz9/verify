import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import FakeSession, app, fake_report, fake_user, override_auth_and_db
from app.models.history import AnalysisMetrics, CacheRegistry, ContentType, Verification


class AiWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_check_text_runs_pipeline_and_persists_analysis(self):
        report = fake_report(summary="Text analysis complete.")
        pipeline_result = {
            "report": report,
            "metrics": {"text_ai_probability": 0.31},
        }

        with (
            patch("app.api.check_text.verify_limit", new=AsyncMock()) as verify_limit,
            patch("app.api.check_text.run_pipeline", new=AsyncMock(return_value=pipeline_result)) as run_pipeline,
        ):
            response = self.client.post(
                "/api/check-text",
                json={"text": "The Earth is flat according to one viral claim."},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), report)
        verify_limit.assert_awaited_once_with(self.user, self.db, "TEXTUAL")
        run_pipeline.assert_awaited_once_with(text="The Earth is flat according to one viral claim.")
        self.assertEqual(self.db.commits, 1)
        self.assertTrue(any(isinstance(item, Verification) for item in self.db.added))
        self.assertTrue(any(isinstance(item, AnalysisMetrics) for item in self.db.added))

    def test_upload_analyzes_image_and_caches_result(self):
        report = fake_report(score=61, verdict="Authentic", summary="Image analysis complete.")

        with (
            patch("app.api.upload.verify_limit", new=AsyncMock()) as verify_limit,
            patch(
                "app.api.upload.check_deepfake",
                new=AsyncMock(return_value={"genai_probability": 0.2, "deepfake_probability": 0.1}),
            ) as check_deepfake,
            patch(
                "app.api.upload.check_ai_image_hf",
                new=AsyncMock(return_value={"ai_probability": 0.25}),
            ) as check_ai_image_hf,
            patch("app.api.upload.generate_final_report", new=AsyncMock(return_value=report)) as final_report,
        ):
            response = self.client.post(
                "/api/upload",
                files={"file": ("sample.png", b"fake image bytes", "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), report)
        verify_limit.assert_awaited_once_with(self.user, self.db, "MEDIA")
        check_deepfake.assert_awaited_once_with(b"fake image bytes")
        check_ai_image_hf.assert_awaited_once_with(b"fake image bytes")
        final_report.assert_awaited_once()
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        cache_entry = next(item for item in self.db.added if isinstance(item, CacheRegistry))
        self.assertEqual(verification.content_type, ContentType.IMAGE)
        self.assertEqual(cache_entry.cached_verdict_id, verification.id)
        self.assertEqual(self.db.commits, 1)


if __name__ == "__main__":
    unittest.main()
