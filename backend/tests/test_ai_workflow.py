import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import FakeSession, app, fake_report, fake_user, override_auth_and_db, valid_png
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
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verification.raw_result["query_input"], "The Earth is flat according to one viral claim.")

    def test_upload_analyzes_valid_image_and_persists_result(self):
        report = fake_report(score=61, verdict="Authentic", summary="Image analysis complete.")

        with (
            patch("app.api.upload.verify_limit", new=AsyncMock()) as verify_limit,
            patch("app.api.upload.analyze_media", new=AsyncMock(return_value=report)) as analyzer,
        ):
            response = self.client.post(
                "/api/upload",
                files={"file": ("sample.png", valid_png(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), report)
        verify_limit.assert_awaited_once_with(self.user, self.db, "MEDIA")
        analyzer.assert_awaited_once()
        self.assertEqual(analyzer.call_args.args[0].kind, "image")
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verification.content_type, ContentType.IMAGE)
        self.assertFalse(any(isinstance(item, CacheRegistry) for item in self.db.added))
        self.assertEqual(self.db.commits, 1)


if __name__ == "__main__":
    unittest.main()
