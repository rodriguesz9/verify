"""Offline metrics for independently labeled predictions; no provider calls.

Positive = refuted claim (veracity) or synthetic/manipulated asset (authenticity).
Never mix factual truth with media origin, or hide abstentions from denominators.
"""
from collections import defaultdict


def evaluate_predictions(records: list[dict]) -> dict:
    groups = defaultdict(list)
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Cada registro deve ser um objeto.")
        identity = (record.get("id"), record.get("dimension"), record.get("split"))
        if not isinstance(identity[0], str) or not identity[0] or identity in seen:
            raise ValueError("ID ausente ou duplicado na mesma dimensão/split.")
        seen.add(identity)
        if record.get("modality") not in {"text", "url", "image", "audio", "video"} or record.get("dimension") not in {"veracity", "authenticity"}:
            raise ValueError("Modalidade/dimensão inválida.")
        if record.get("split") not in {"calibration", "test"}:
            raise ValueError("Separe calibration de test; não calibre no teste.")
        if record.get("expected") not in {"positive", "negative"} or record.get("predicted") not in {"positive", "negative", "inconclusive"}:
            raise ValueError("Rótulo/predição inválido.")
        if not isinstance(record.get("ground_truth_source"), str) or not record["ground_truth_source"].strip():
            raise ValueError("Ground truth exige fonte independente/documentada.")
        groups[(record["modality"], record["dimension"], record["split"])].append(record)

    def ratio(a, b):
        return round(a / b, 6) if b else None
    results = []
    for (modality, dimension, split), rows in sorted(groups.items()):
        matrix = {truth: {prediction: 0 for prediction in ("positive", "negative", "inconclusive")}
                  for truth in ("positive", "negative")}
        for row in rows:
            matrix[row["expected"]][row["predicted"]] += 1
        tp, fp = matrix["positive"]["positive"], matrix["negative"]["positive"]
        tn, fn = matrix["negative"]["negative"], matrix["positive"]["negative"]
        positive_count, negative_count = sum(matrix["positive"].values()), sum(matrix["negative"].values())
        results.append({"modality": modality, "dimension": dimension, "split": split,
            "positive_definition": "refuted_claim" if dimension == "veracity" else "synthetic_or_manipulated_media",
            "n": len(rows), "confusion_matrix_including_abstentions": matrix,
            "coverage": ratio(tp + fp + tn + fn, len(rows)), "precision": ratio(tp, tp + fp),
            "effective_recall": ratio(tp, positive_count), "false_positive_rate": ratio(fp, negative_count),
            "false_negative_rate": ratio(fn, positive_count),
            "positive_abstention_rate": ratio(matrix["positive"]["inconclusive"], positive_count),
            "negative_abstention_rate": ratio(matrix["negative"]["inconclusive"], negative_count),
            "selective_accuracy": ratio(tp + tn, tp + fp + tn + fn)})
    return {"scope": "Metrics of submitted labeled records only; not a guarantee for new content.",
            "warning": "Small/biased datasets or leaked labels cannot establish production accuracy. Use disjoint generators/speakers/events and versions.",
            "groups": results}
