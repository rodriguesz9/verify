"""Accuracy must keep abstentions, modalities and evaluation splits visible."""
import unittest

from app.services.benchmark_metrics import evaluate_predictions


def record(identifier, expected, predicted, **overrides):
    return {"id": identifier, "modality": "text", "dimension": "veracity",
            "split": "test", "expected": expected, "predicted": predicted,
            "ground_truth_source": "Synthetic control, not application accuracy", **overrides}


class AccuracyDenominatorTests(unittest.TestCase):
    def test_selective_accuracy_cannot_hide_half_abstaining(self):
        rows = [record("a", "positive", "positive"), record("b", "negative", "negative"),
                record("c", "positive", "inconclusive"), record("d", "negative", "inconclusive")]
        group = evaluate_predictions(rows)["groups"][0]
        self.assertEqual(group["selective_accuracy"], 1)
        self.assertEqual(group["accuracy_including_abstentions"], .5)
        self.assertEqual(group["abstention_rate"], .5)
        self.assertEqual((group["correct_count"], group["wrong_conclusive_count"], group["inconclusive_count"]),
                         (2, 0, 2))

    def test_wrong_conclusions_and_abstentions_are_different_counts(self):
        group = evaluate_predictions([record("a", "positive", "negative"),
                                      record("b", "negative", "positive"),
                                      record("c", "negative", "inconclusive")])["groups"][0]
        self.assertEqual(group["correct_count"], 0)
        self.assertEqual(group["wrong_conclusive_count"], 2)
        self.assertEqual(group["inconclusive_count"], 1)
        self.assertEqual(group["accuracy_including_abstentions"], 0)

    def test_no_conclusions_is_zero_overall_not_a_fake_perfect_score(self):
        group = evaluate_predictions([record("a", "negative", "inconclusive")])["groups"][0]
        self.assertEqual(group["accuracy_including_abstentions"], 0)
        self.assertEqual(group["abstention_rate"], 1)
        self.assertIsNone(group["selective_accuracy"])
        self.assertEqual(evaluate_predictions([])["groups"], [])

    def test_totals_are_computed_per_modality_dimension_and_split_only(self):
        groups = evaluate_predictions([
            record("a", "positive", "positive"),
            record("b", "negative", "inconclusive", split="calibration"),
            record("c", "positive", "negative", modality="image", dimension="authenticity"),
        ])["groups"]
        self.assertEqual(len(groups), 3)
        for group in groups:
            self.assertEqual(group["n"], group["correct_count"] + group["wrong_conclusive_count"]
                             + group["inconclusive_count"])
