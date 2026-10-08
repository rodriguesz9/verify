import unittest
import copy
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from helpers import FakeSession, app, fake_report, fake_user, override_auth_and_db, valid_png
from app.models.history import AnalysisMetrics, CacheRegistry, ContentType, Verification
from app.services.pdf_snapshot import verify_pdf_snapshot


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
        returned = response.json()
        self.assertEqual({key: returned[key] for key in report}, report)
        self.assertEqual(returned["content_type"], "text")
        self.assertIsNotNone(datetime.fromisoformat(returned["analyzed_at"]).tzinfo)
        self.assertEqual(returned["pdf_export_status"], "unavailable")  # incomplete legacy fixture
        verify_limit.assert_awaited_once_with(self.user, self.db, "TEXTUAL")
        run_pipeline.assert_awaited_once_with(text="The Earth is flat according to one viral claim.")
        self.assertEqual(self.db.commits, 1)
        self.assertTrue(any(isinstance(item, Verification) for item in self.db.added))
        self.assertTrue(any(isinstance(item, AnalysisMetrics) for item in self.db.added))
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verification.raw_result["query_input"], "The Earth is flat according to one viral claim.")

    def test_upload_analyzes_valid_image_and_persists_result(self):
        report = fake_report(score=61, verdict="Suspicious", summary="Image analysis complete.",
                             content_type="image", forensics={}, plain_explanation="Image analysis complete.",
                             elderly_tip="Confirm the original source.")
        original_report = copy.deepcopy(report)

        with (
            patch("app.api.upload.verify_limit", new=AsyncMock()) as verify_limit,
            patch("app.api.upload.analyze_media", new=AsyncMock(return_value=report)) as analyzer,
        ):
            response = self.client.post(
                "/api/upload",
                files={"file": ("sample.png", valid_png(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual({key: result[key] for key in original_report}, original_report)
        self.assertEqual(report, original_report)  # Metadata/export must not mutate provider output.
        self.assertEqual(result["filename"], "sample.png")
        self.assertEqual(result["file_hash_sha256"], hashlib.sha256(valid_png()).hexdigest())
        self.assertIsNotNone(datetime.fromisoformat(result["analyzed_at"]).tzinfo)
        self.assertEqual(result["pdf_export_status"], "ready")
        verify_limit.assert_awaited_once_with(self.user, self.db, "MEDIA")
        analyzer.assert_awaited_once()
        self.assertEqual(analyzer.call_args.args[0].kind, "image")
        verification = next(item for item in self.db.added if isinstance(item, Verification))
        self.assertEqual(verification.content_type, ContentType.IMAGE)
        self.assertEqual(verification.raw_result,
                         {**original_report, "filename": "sample.png", "file_hash_sha256": result["file_hash_sha256"],
                          "analyzed_at": result["analyzed_at"]})
        self.assertFalse(any(key.startswith("pdf_") for key in verification.raw_result))
        self.assertEqual(verify_pdf_snapshot(result["pdf_snapshot_token"], self.user), verification.raw_result)
        self.assertFalse(any(isinstance(item, CacheRegistry) for item in self.db.added))
        self.assertEqual(self.db.commits, 1)


if __name__ == "__main__":
    unittest.main()
