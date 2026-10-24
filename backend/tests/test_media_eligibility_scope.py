"""Detector-policy boundaries; simulated data, not provider-accuracy evidence."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import helpers  # disables private dotenv/provider credentials before app imports
from helpers import valid_wav
from app.services.evidence_policy import media_report
from app.services.hive_service import (
    HIVE_V3_MODEL, HiveV3Budget, check_hive_media, parse_hive_scores, parse_hive_v3_scores,
)
from app.services.media_analysis import analyze_media
from app.services.media_validation import ValidatedMedia


def detector(**fields):
    return {"available": True, "status": "success", **fields}


def v3_output(start=None, end=None, score=.99, *, label="ai_generated_audio"):
    return {"time": start, "end_time": end, "classes": [{"class": label, "value": score}]}


def v3_payload(*outputs):
    return {"model": HIVE_V3_MODEL, "output": list(outputs)}


class MediaEligibilityBoundaryTests(unittest.TestCase):
    def test_nonvoting_dedicated_head_does_not_mask_eligible_base_head(self):
        for marker in ({"voting_eligible": False}, {"decision_role": "experimental_signal"}):
            for score in (.01, .99):
                with self.subTest(marker=marker, score=score):
                    report = media_report({
                        "hive": detector(deepfake_score=.99),
                        "hive_deepfake": detector(deepfake_score=score, **marker),
                        "sightengine": detector(deepfake_probability=.99),
                    })
                    self.assertEqual(report["verdict"], "Manipulated")
                    self.assertEqual(report["media_signal"]["state"], "consensus_manipulation")
                    self.assertEqual(report["media_signal"]["independent_provider_count"], 2)
                    self.assertFalse(report["detector_disagreement"])
                    coverage = report["provider_coverage"]
                    self.assertEqual(coverage["hive"]["deepfake_score"], .99)
                    self.assertEqual(coverage["hive_deepfake"]["deepfake_score"], score)
                    self.assertEqual(coverage["hive_deepfake"]["status"], "success")
                    self.assertFalse(coverage["hive_deepfake"]["voting_eligible"])
                    self.assertIn("não habilitada", coverage["hive_deepfake"]["reason"])

    def test_eligible_dedicated_head_keeps_precedence_and_one_provider_vote(self):
        report = media_report({
            "hive": detector(deepfake_score=.99),
            "hive_deepfake": detector(deepfake_score=.01),
            "sightengine": detector(deepfake_probability=.99),
        })
        self.assertEqual(report["verdict"], "Suspicious")
        self.assertTrue(report["detector_disagreement"])
        self.assertEqual(report["media_signal"]["state"], "disagreement")
        self.assertEqual(report["provider_coverage"]["hive"]["deepfake_score"], .99)
        report = media_report({"hive": detector(deepfake_score=.99),
                               "hive_deepfake": detector(deepfake_score=.99)})
        self.assertEqual(report["verdict"], "Suspicious")
        self.assertEqual(report["media_signal"]["independent_provider_count"], 1)

    def test_ineligible_base_cannot_replace_ineligible_dedicated(self):
        report = media_report({
            "hive": detector(deepfake_score=.99, voting_eligible=False),
            "hive_deepfake": detector(deepfake_score=.99, decision_role="experimental_signal"),
            "sightengine": detector(deepfake_probability=.99),
        })
        self.assertEqual(report["verdict"], "Suspicious")
        self.assertEqual(report["media_signal"]["state"], "isolated_manipulation")
        self.assertEqual(report["media_signal"]["valid_providers"]["manipulation"], ["sightengine"])

    def test_experimental_generation_and_facial_heads_cannot_confirm_or_disagree(self):
        for marker in ({"voting_eligible": False}, {"decision_role": "experimental_signal"}):
            for score in (.01, .99):
                with self.subTest(marker=marker, score=score):
                    report = media_report({
                        "hive": detector(ai_generated_score=.99, deepfake_score=.99),
                        "sightengine": detector(genai_probability=score, deepfake_probability=score, **marker),
                        "huggingface": detector(ai_probability=.99, **marker),
                    })
                    self.assertEqual(report["verdict"], "Suspicious")
                    self.assertFalse(report["detector_disagreement"])
                    self.assertEqual(report["media_signal"]["independent_provider_count"], 1)
                    self.assertFalse(report["provider_coverage"]["sightengine"]["voting_eligible"])

    def test_experimental_facial_head_does_not_erase_generation_consensus(self):
        report = media_report({
            "hive": detector(ai_generated_score=.99, deepfake_score=.99),
            "sightengine": detector(genai_probability=.99),
            "hive_deepfake": detector(deepfake_score=.01, decision_role="experimental_signal"),
        })
        self.assertEqual(report["verdict"], "AI_Generated")
        self.assertEqual(report["analysis_status"], "partial")
        self.assertFalse(report["detector_disagreement"])

    def test_original_error_reason_and_status_are_not_overwritten(self):
        report = media_report({"hive_deepfake": {
            "available": False, "status": "timeout", "reason": "Prazo do detector atingido.",
            "decision_role": "experimental_signal",
        }})
        coverage = report["provider_coverage"]["hive_deepfake"]
        self.assertEqual(coverage["status"], "timeout")
        self.assertEqual(coverage["reason"], "Prazo do detector atingido.")
        self.assertFalse(coverage["voting_eligible"])


class VideoEligibilityBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_eligibility_is_applied_in_same_frame_before_video_aggregation(self):
        media = ValidatedMedia(b"control", "control.mp4", "video/mp4", "video",
                               {"duration_seconds": 3, "has_audio": False})
        frame = {"hive": detector(deepfake_score=.99),
                 "hive_deepfake": detector(deepfake_score=.01, decision_role="experimental_signal"),
                 "sightengine": detector(deepfake_probability=.99)}
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(
                return_value=([(1.5, b"frame")], [frame]))):
            report = await analyze_media(media)
        self.assertEqual(report["verdict"], "Manipulated")
        self.assertEqual(report["flagged_timestamps_seconds"], [1.5])
        self.assertEqual(report["forensics"]["video"]["frames"][0]["verdict"], "Manipulated")

    async def test_experimental_other_frame_cannot_manufacture_consensus(self):
        media = ValidatedMedia(b"control", "control.mp4", "video/mp4", "video",
                               {"duration_seconds": 3, "has_audio": False})
        frames = [{"hive": detector(deepfake_score=.99)},
                  {"sightengine": detector(deepfake_probability=.99, voting_eligible=False)}]
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(
                return_value=([(0.5, b"one"), (2.5, b"two")], frames))):
            report = await analyze_media(media)
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["flagged_timestamps_seconds"], [])


class HiveSegmentBoundaryTests(unittest.TestCase):
    def test_v3_preserves_local_scores_not_aggregate_maximum_in_each_segment(self):
        report = parse_hive_v3_scores(v3_payload(v3_output(0, 1, .01), v3_output(1, 5, .99)),
                                      "audio", duration_seconds=5)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["ai_generated_score"], .99)
        self.assertEqual(report["segments"], [
            {"start_seconds": 0, "end_seconds": 1, "ai_generated_score": .01},
            {"start_seconds": 1, "end_seconds": 5, "ai_generated_score": .99},
        ])
        self.assertEqual(report["score_aggregation"], "maximum_valid_observation_not_probability_of_whole_file")

    def test_out_of_file_coordinates_are_omitted_not_clipped_or_made_whole_file(self):
        report = parse_hive_v3_scores(v3_payload(v3_output(0, 1, .01), v3_output(4, 6, .98),
                                                v3_output(100, 110, .99)), "audio", duration_seconds=5)
        self.assertEqual(report["segments"], [{"start_seconds": 0, "end_seconds": 1, "ai_generated_score": .01}])
        self.assertEqual(report["ai_generated_score"], .99)
        self.assertEqual(report["status"], "success", "Coordinates do not rewrite a valid detector response")

    def test_invalid_coordinates_cannot_create_segment_but_do_not_rewrite_score(self):
        for start, end in ((True, 1), (0, False), ("0", 1), (0, "1"), (float("nan"), 1),
                           (0, float("inf")), (-1, 1), (2, 1), (0, 121), (None, 1), (0, None)):
            with self.subTest(start=start, end=end):
                report = parse_hive_v3_scores(v3_payload(v3_output(start, end)), "audio", duration_seconds=5)
                self.assertEqual(report["segments"], [])
                self.assertEqual(report["ai_generated_score"], .99)
                self.assertEqual(report["status"], "success")
                json.dumps(report, allow_nan=False)

    def test_invalid_duration_never_promotes_coordinates_to_validated_scope(self):
        for duration in (True, False, "5", 0, -1, 121, float("nan"), float("inf")):
            with self.subTest(duration=duration):
                report = parse_hive_v3_scores(v3_payload(v3_output(0, 1)), "audio", duration_seconds=duration)
                self.assertEqual(report["segments"], [])
                self.assertEqual(report["ai_generated_score"], .99)

    def test_missing_coordinates_do_not_fabricate_whole_file_segment(self):
        report = parse_hive_v3_scores(v3_payload(v3_output()), "audio", duration_seconds=5)
        self.assertEqual(report["segments"], [])
        self.assertEqual(report["status"], "success")

    def test_legacy_parser_signature_and_120_second_cap_remain_compatible(self):
        report = parse_hive_v3_scores(v3_payload(v3_output(100, 110)), "audio")
        self.assertEqual(report["segments"][0]["end_seconds"], 110)
        payload = {"status": [{"status": {"code": "0"}, "response": {"output": [
            {"time": 0, "end_time": 5, "classes": [{"class": "ai_generated", "score": .8}]}]}}]}
        self.assertEqual(len(parse_hive_scores(payload)["segments"]), 1)
        self.assertEqual(parse_hive_scores(payload, duration_seconds=4)["segments"], [])

    def test_visual_or_facial_head_cannot_become_audio_temporal_observation(self):
        for label in ("ai_generated", "deepfake", "not_ai_generated_audio"):
            with self.subTest(label=label):
                report = parse_hive_v3_scores(v3_payload(v3_output(0, 1, label=label)), "audio", duration_seconds=5)
                self.assertFalse(report["available"])
                self.assertEqual(report["segments"], [])


class HiveValidatedDurationTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_passes_validated_duration_to_parser_without_retry(self):
        payload = v3_payload(v3_output(0, 1, .01), v3_output(4, 6, .98), v3_output(100, 110, .99))
        with patch.dict(os.environ, {"HIVE_API_VERSION": "v3", "HIVE_V3_API_KEY": "offline-test-only",
                "HIVE_V3_MEDIA_TYPES": "audio", "HIVE_V3_AUDIO_SECONDS_LIMIT": "5"}), \
             patch("app.services.hive_service.hive_v3_budget", HiveV3Budget()), \
             patch("httpx.AsyncClient.post", new=AsyncMock(return_value=httpx.Response(200, json=payload))) as post:
            report = await check_hive_media(valid_wav(), "control.wav", "audio", "audio/wav", duration_seconds=5)
        self.assertEqual(post.await_count, 1)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["ai_generated_score"], .99)
        self.assertEqual(report["segments"], [{"start_seconds": 0, "end_seconds": 1, "ai_generated_score": .01}])
