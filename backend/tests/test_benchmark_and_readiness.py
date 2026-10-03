import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from helpers import app, valid_wav
from app.services.benchmark_metrics import evaluate_predictions
from app.services.audio_service import analyze_audio_quick_for_demonstration
from app.services.c2pa_service import parse_c2pa_report


def row(index, expected, predicted, dimension="authenticity", modality="audio", split="test"):
    return {"id": str(index), "modality": modality, "dimension": dimension, "split": split,
            "expected": expected, "predicted": predicted, "ground_truth_source": "Synthetic unit-test provenance, not production evidence"}


class MetricsTests(unittest.TestCase):
    def test_abstentions_not_hidden_from_coverage_or_recall(self):
        result = evaluate_predictions([row(1, "positive", "positive"), row(2, "positive", "inconclusive"),
                                       row(3, "negative", "positive"), row(4, "negative", "negative")])["groups"][0]
        self.assertEqual(result["coverage"], .75)
        self.assertEqual(result["precision"], .5)
        self.assertEqual(result["effective_recall"], .5)
        self.assertEqual(result["false_positive_rate"], .5)
        self.assertEqual(result["positive_abstention_rate"], .5)

    def test_no_predictions_has_no_fake_accuracy(self):
        result = evaluate_predictions([row(1, "negative", "inconclusive")])["groups"][0]
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["selective_accuracy"])
        self.assertEqual(result["coverage"], 0)

    def test_modalities_dimensions_and_splits_not_pooled(self):
        records = [row(1, "positive", "positive"), row(2, "positive", "positive", modality="image"),
                   row(3, "positive", "positive", dimension="veracity", modality="text"),
                   row(4, "positive", "positive", split="calibration")]
        self.assertEqual(len(evaluate_predictions(records)["groups"]), 4)

    def test_labels_require_documented_provenance_and_disjoint_ids(self):
        base = row(1, "positive", "positive")
        for records in ([base, base], [{**base, "ground_truth_source": ""}], [{**base, "split": "train"}],
                        [{**base, "expected": "unknown"}], [{**base, "dimension": "truthiness"}]):
            with self.assertRaises(ValueError):
                evaluate_predictions(records)

    def test_capabilities_do_not_expose_secret_or_promise_health(self):
        with patch.dict(os.environ, {"GOOGLE_FACT_CHECK_KEY": "sensitive-unit-test-value"}):
            data = TestClient(app).get("/api/capabilities").json()
        self.assertTrue(data["providers"]["google_fact_check"]["configured"])
        self.assertEqual(data["providers"]["google_fact_check"]["operational_status"], "not_tested")
        self.assertNotIn("sensitive-unit-test-value", str(data))

    def test_c2pa_missing_validation_is_not_trusted(self):
        with self.assertRaises(ValueError):
            parse_c2pa_report({"active_manifest": {"assertions": []}}, True)


class TranscriptionFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_assembly_fallback_transcribes_but_never_certifies_voice(self):
        with patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "test-only"}), \
             patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock(return_value="")), \
             patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock(return_value={"status": "success", "transcription": "Minha avó chegou para o café"})):
            report = await analyze_audio_quick_for_demonstration(valid_wav())
        self.assertEqual(report["transcription_provider"], "assemblyai")
        self.assertEqual(report["verdict"], "inconclusiva")
        self.assertIsNone(report["score_percent"])
