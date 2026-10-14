"""Public local-control diagnostic records never publish bearer capabilities."""
import unittest
from scripts.validation_api_probe import CONTROLS, REPORT_FIELDS, sanitize


class LocalAPIProbeTests(unittest.TestCase):
    def test_nested_credentials_and_raw_provider_objects_are_removed(self):
        source = {"verdict": "AI_Generated", "pdf_snapshot_token": "not-for-output",
                  "provider_coverage": {"hive": {"status": "success", "apiKey": "not-for-output",
                                                "headers": {"Authorization": "not-for-output"}}},
                  "forensics": {"raw": {"request": {"id": "not-for-output"}}, "raw_preview": {},
                                "text_review_token": "not-for-output", "ai_score": .99}}
        self.assertEqual(sanitize(source), {"verdict": "AI_Generated", "provider_coverage": {"hive": {"status": "success"}},
                                           "forensics": {"ai_score": .99}})

    def test_public_controls_keep_actual_context_without_claiming_whole_article(self):
        self.assertEqual(CONTROLS["queen_link"]["expected_veracity"], "not_prespecified")
        self.assertIn("Authored false", CONTROLS["queen_false"]["provenance"])
        self.assertIn("no voice cloning", CONTROLS["synthetic_audio"]["provenance"])
        self.assertTrue({"provider_coverage", "claim_assessments", "content_analysis", "text_review_status"} <= REPORT_FIELDS)
        self.assertNotIn("pdf_snapshot_token", REPORT_FIELDS)


if __name__ == "__main__":
    unittest.main()
