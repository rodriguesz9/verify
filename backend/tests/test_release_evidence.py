"""Release policy regressions: offline assertions, never provider accuracy claims."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import helpers  # disables provider credentials before application imports
from app.services.c2pa_service import AI_SOURCE_TYPE, parse_c2pa_report, verify_c2pa
from app.services.evidence_policy import media_report
from app.services.media_analysis import analyze_media
from app.services.media_validation import ValidatedMedia


def manifest(assertions, statuses=None):
    return {"active_manifest": "control", "manifests": {"control": {"assertions": assertions}},
            "validation_status": [] if statuses is None else statuses}


def creation_assertion(label="c2pa.actions", **action_overrides):
    action = {"action": "c2pa.created", "digitalSourceType": AI_SOURCE_TYPE, **action_overrides}
    return {"label": label, "data": {"actions": [action]}}


class C2PAStructureTests(unittest.TestCase):
    def test_exact_creation_action_v1_and_v2_requires_explicit_trusted_input(self):
        for label in ("c2pa.actions", "c2pa.actions.v2"):
            with self.subTest(label=label):
                data = manifest([creation_assertion(label)])
                untrusted = parse_c2pa_report(data)
                self.assertEqual(untrusted["validation_state"], "present_unverified_trust")
                self.assertTrue(untrusted["unverified_ai_marker"])
                self.assertFalse(untrusted["generative_ai_flag"])
                self.assertFalse(untrusted["voting_eligible"])
                trusted = parse_c2pa_report(data, trust_configured=True)
                self.assertTrue(trusted["generative_ai_flag"])

    def test_ai_words_in_comments_metadata_and_non_creation_actions_never_vote(self):
        controls = [
            {"label": "com.example.description", "data": {"text": AI_SOURCE_TYPE}},
            {"label": "c2pa.actions", "data": {"digitalSourceType": AI_SOURCE_TYPE}},
            creation_assertion(description="This is NOT trainedAlgorithmicMedia", digitalSourceType="digitalCapture"),
            creation_assertion("c2pa.actions.untrusted"),
            creation_assertion(action="c2pa.resized"),
            creation_assertion(digitalSourceType="trainedAlgorithmicMedia"),
            creation_assertion(digitalSourceType=AI_SOURCE_TYPE + "-not"),
            {"label": "c2pa.actions", "data": {"actions": None}},
            {"label": "c2pa.actions", "data": {"actions": ["trainedAlgorithmicMedia", None]}},
            {"label": {"invalid": "c2pa.actions"}, "data": {"actions": ["trainedAlgorithmicMedia"]}},
        ]
        for assertion in controls:
            with self.subTest(assertion=assertion):
                parsed = parse_c2pa_report(manifest([assertion]), trust_configured=True)
                self.assertFalse(parsed["generative_ai_flag"])
                self.assertFalse(parsed["unverified_ai_marker"])
                self.assertEqual(media_report({"c2pa": parsed})["analysis_status"], "inconclusive")

    def test_validation_failures_and_truthy_non_boolean_trust_cannot_certify(self):
        data = manifest([creation_assertion()], [{"code": "claimSignature.mismatch"}])
        invalid = parse_c2pa_report(data, trust_configured=True)
        self.assertEqual(invalid["validation_state"], "invalid")
        self.assertFalse(invalid["generative_ai_flag"])
        self.assertFalse(invalid["voting_eligible"])
        for value in ("true", "/tmp/not-an-anchor.pem", 1):
            with self.subTest(value=value):
                parsed = parse_c2pa_report(manifest([creation_assertion()]), trust_configured=value)
                self.assertNotEqual(parsed["validation_state"], "valid")
                self.assertFalse(parsed["generative_ai_flag"])

    def test_malformed_manifest_and_assertion_containers_rejected(self):
        for data in ([], {"active_manifest": "missing", "manifests": []},
                     manifest({"label": "c2pa.actions"}), manifest([], statuses="success")):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_c2pa_report(data, trust_configured=True)


class RuntimeC2PATests(unittest.IsolatedAsyncioTestCase):
    async def test_env_presence_and_cli_empty_errors_do_not_homologate_runtime(self):
        output = json.dumps(manifest([creation_assertion()])).encode()
        for anchors in ("/tmp/not-an-anchor.pem", "https://example.test/trust.pem", "false"):
            with self.subTest(anchors=anchors), \
                 patch.dict(os.environ, {"C2PATOOL_ENABLED": "true", "C2PATOOL_TRUST_ANCHORS": anchors}), \
                 patch("app.services.c2pa_service.shutil.which", return_value="/test/c2patool"), \
                 patch("app.services.c2pa_service.run_media_tool", new=AsyncMock(return_value=output)) as tool:
                parsed = await verify_c2pa(b"c2pa-control", "control.jpg")
                self.assertEqual(parsed["tool_status"], "success")
                self.assertEqual(parsed["validation_state"], "present_unverified_trust")
                self.assertTrue(parsed["unverified_ai_marker"])
                self.assertFalse(parsed["generative_ai_flag"])
                self.assertFalse(parsed["trust_homologated"])
                self.assertFalse(parsed["voting_eligible"])
                self.assertEqual(media_report({"c2pa": parsed})["analysis_status"], "inconclusive")
                self.assertEqual(len(tool.call_args.args), 2)
                self.assertNotIn("trust", tool.call_args.args)

    async def test_cli_failure_falls_back_to_non_voting_binary_hint(self):
        with patch.dict(os.environ, {"C2PATOOL_ENABLED": "true", "C2PATOOL_TRUST_ANCHORS": "fake"}), \
             patch("app.services.c2pa_service.shutil.which", return_value="/test/c2patool"), \
             patch("app.services.c2pa_service.run_media_tool", new=AsyncMock(side_effect=ValueError("private-error"))):
            parsed = await verify_c2pa(b"c2pa trainedAlgorithmicMedia", "control.jpg")
        self.assertTrue(parsed["has_c2pa"])
        self.assertFalse(parsed["generative_ai_flag"])
        self.assertFalse(parsed["voting_eligible"])
        self.assertNotIn("private-error", str(parsed))


class VideoAudioDimensionTests(unittest.IsolatedAsyncioTestCase):
    async def _analyze(self, frame, audio):
        media = ValidatedMedia(b"control", "control.mp4", "video/mp4", "video",
                               {"duration_seconds": 2, "has_audio": True})
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=([(1, b"frame")], [frame]))), \
             patch("app.services.media_analysis.video_audio_layers", new=AsyncMock(return_value=audio)):
            return await analyze_media(media, review_first=True)

    async def test_only_acoustic_consensus_has_coherent_index_flags_and_dimensions(self):
        track = media_report({"hive": {"available": True, "status": "success", "ai_generated_score": .99},
                              "sightengine_audio": {"available": True, "status": "success", "ai_speech_score": .98}}, "audio")
        report = await self._analyze({}, track)
        self.assertEqual(report["verdict"], "AI_Generated")
        self.assertEqual(report["authenticity_status"], "ai_indications")
        self.assertEqual(report["analysis_status"], "partial")
        self.assertEqual(report["score"], 20)
        self.assertEqual(report["score_semantics"], "legacy_decision_index_not_probability")
        self.assertEqual(report["visual_authenticity_status"], "undetermined")
        self.assertEqual(report["visual_analysis_status"], "inconclusive")
        self.assertEqual(report["audio_analysis"]["authenticity_status"], "ai_indications")
        self.assertEqual(report["flagged_timestamps_seconds"], [])
        self.assertEqual(report["forensics"]["video"]["frames"][0]["verdict"], "Suspicious")
        self.assertTrue(any("faixa de áudio" in flag for flag in report["red_flags"]))
        self.assertIn("origem visual", report["summary"])
        self.assertIn("não verifica o vídeo inteiro", report["summary"])
        self.assertTrue(any("não comprovam clonagem" in item for item in report["limitations"]))
        self.assertEqual(report["plain_explanation"], report["summary"])
        self.assertEqual(report["whatsapp_share_text"], report["summary"])
        self.assertIsNone(report["authenticity_percentage"])
        json.dumps(report, allow_nan=False)

    async def test_facial_dimension_survives_acoustic_consensus(self):
        frame = {"sightengine": {"available": True, "status": "success", "deepfake_probability": .99},
                 "hive": {"available": True, "status": "success", "deepfake_score": .98}}
        track = media_report({"hive": {"available": True, "status": "success", "ai_generated_score": .99},
                              "sightengine_audio": {"available": True, "status": "success", "ai_speech_score": .98}}, "audio")
        report = await self._analyze(frame, track)
        self.assertEqual(report["verdict"], "Manipulated")
        self.assertEqual(report["visual_authenticity_status"], "manipulation_indications")
        self.assertEqual(report["authenticity_status"], "manipulation_indications")
        self.assertEqual(report["audio_analysis"]["authenticity_status"], "ai_indications")
        self.assertEqual(report["score"], 20)
        self.assertIn(1, report["flagged_timestamps_seconds"])
        self.assertTrue(any("manipulação facial" in flag for flag in report["red_flags"]))
        self.assertTrue(any("faixa de áudio" in flag for flag in report["red_flags"]))

    async def test_audio_disagreement_preserved_without_fabricating_global_indications(self):
        track = media_report({"hive": {"available": True, "status": "success", "ai_generated_score": .99},
                              "sightengine_audio": {"available": True, "status": "success", "ai_speech_score": .1}}, "audio")
        report = await self._analyze({}, track)
        self.assertTrue(report["detector_disagreement"])
        self.assertFalse(report["visual_detector_disagreement"])
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["authenticity_status"], "undetermined")
        self.assertEqual(report["red_flags"], [])
        self.assertEqual(report["score"], 50)


if __name__ == "__main__":
    unittest.main()
