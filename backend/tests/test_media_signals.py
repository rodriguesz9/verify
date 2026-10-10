"""Presentation diagnostics, not new detector decisions or an accuracy benchmark."""
import json
import unittest
from unittest.mock import AsyncMock, patch

import helpers  # disables credentials and dotenv before application imports
from app.services.evidence_policy import media_report, forensic_contract, POLICY_VERSION
from app.services.media_analysis import analyze_media, video_media_signal
from app.services.media_validation import ValidatedMedia


def detector(**scores):
    return {"available": True, "status": "success", **scores}


class MediaSignalTests(unittest.TestCase):
    def test_generated_audio_hive_signal_stays_isolated_and_inconclusive(self):
        report = media_report({"hive": detector(ai_generated_score=.974),
                               "sightengine_audio": {"available": False, "status": "disabled"},
                               "audio": {"transcription": "Bora acordar"}}, "audio")
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "isolated_ai")
        self.assertEqual(signal["scope"], "audio")
        self.assertEqual(signal["independent_provider_count"], 1)
        self.assertEqual(signal["ai_provider_count"], 1)
        self.assertEqual(signal["manipulation_provider_count"], 0)
        self.assertEqual(signal["strong_providers"], {"ai": ["hive"], "manipulation": []})
        self.assertEqual((report["verdict"], report["analysis_status"], report["authenticity_status"]),
                         ("Suspicious", "inconclusive", "undetermined"))
        self.assertEqual(report["score"], 50)
        self.assertIsNone(report["confidence"])
        self.assertIsNone(report["authenticity_percentage"])
        self.assertEqual(report["red_flags"], [])
        self.assertEqual(report["policy_version"], POLICY_VERSION)
        self.assertEqual(signal["version"], "1")
        self.assertIn("possível fala sintética", report["summary"])
        self.assertIn("ainda não confirma a origem da voz", report["summary"])
        self.assertIn("não comprova clonagem", report["summary"])
        self.assertEqual(report["plain_explanation"], report["summary"])
        self.assertIn(report["summary"], report["whatsapp_share_text"])
        self.assertNotRegex(report["whatsapp_share_text"], r"Hive|Sightengine|97\.4|%")

    def test_two_low_responses_are_not_a_certificate_of_authenticity(self):
        report = media_report({"hive": detector(ai_generated_score=0),
                               "sightengine": detector(genai_probability=.001)})
        self.assertEqual(report["media_signal"]["state"], "no_high_signal")
        self.assertEqual(report["media_signal"]["independent_provider_count"], 2)
        self.assertEqual(report["media_signal"]["strong_providers"]["ai"], [])
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["authenticity_status"], "undetermined")
        self.assertNotEqual(report["verdict"], "Authentic")

    def test_facial_score_cannot_supply_an_acoustic_provider_or_voice_signal(self):
        report = media_report({"hive": detector(deepfake_score=.99),
                               "sightengine": detector(deepfake_probability=.99)}, "audio")
        self.assertEqual(report["media_signal"]["state"], "unavailable")
        self.assertEqual(report["media_signal"]["independent_provider_count"], 0)
        self.assertEqual(report["media_signal"]["strong_providers"]["manipulation"], [])
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertIn("não permitiram analisar a origem deste áudio", report["summary"])
        self.assertNotRegex(report["summary"], r"voz|fala sintética|manipulação facial")

    def test_inconclusive_public_explanations_distinguish_observations_without_vendor_scores(self):
        cases = (
            ({"hive": detector(ai_generated_score=.99)}, "isolated_ai", "Falta confirmação independente"),
            ({"hive": detector(deepfake_score=.99)}, "isolated_manipulation", "possível manipulação facial"),
            ({"hive": detector(ai_generated_score=.99), "sightengine": detector(genai_probability=.01)},
             "disagreement", "Detectores discordaram"),
            ({"hive": detector(ai_generated_score=.01)}, "no_high_signal", "Isso não comprova autenticidade"),
            ({"hive": {"available": False, "status": "disabled"}}, "unavailable", "não permitiram analisar a origem"),
        )
        for forensics, state, phrase in cases:
            with self.subTest(state=state):
                report = media_report(forensics)
                self.assertEqual(report["media_signal"]["state"], state)
                self.assertEqual(report["analysis_status"], "inconclusive")
                self.assertIn(phrase, report["summary"])
                self.assertEqual(report["summary"], report["plain_explanation"])
                self.assertIn(report["summary"], report["whatsapp_share_text"])
                self.assertNotRegex(report["whatsapp_share_text"], r"Hive|Sightengine|Hugging|%")

    def test_high_low_disagreement_is_distinct_from_unconfirmed_signal(self):
        report = media_report({"hive": detector(ai_generated_score=.99),
                               "sightengine": detector(genai_probability=.01)})
        self.assertEqual(report["media_signal"]["state"], "disagreement")
        self.assertEqual(report["media_signal"]["strong_providers"]["ai"], ["hive"])
        self.assertTrue(report["detector_disagreement"])
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_existing_thresholds_and_consensus_decision_stay_unchanged(self):
        for score, state, verdict, status in ((.79, "no_high_signal", "Suspicious", "inconclusive"),
                                              (.8, "consensus_ai", "AI_Generated", "partial")):
            with self.subTest(score=score):
                report = media_report({"hive": detector(ai_generated_score=score),
                                       "sightengine": detector(genai_probability=score)})
                self.assertEqual(report["media_signal"]["state"], state)
                self.assertEqual((report["verdict"], report["analysis_status"]), (verdict, status))
        report = media_report({"hive": detector(ai_generated_score=.8),
                               "sightengine": detector(genai_probability=.2)})
        self.assertEqual(report["media_signal"]["state"], "disagreement")

    def test_face_only_responses_count_valid_provider_families(self):
        report = media_report({"hive_deepfake": detector(deepfake_score=.98),
                               "sightengine": detector(deepfake_probability=.99)})
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "consensus_manipulation")
        self.assertEqual(signal["independent_provider_count"], 2)
        self.assertEqual(signal["ai_provider_count"], 0)
        self.assertEqual(signal["manipulation_provider_count"], 2)
        self.assertEqual(signal["strong_providers"]["manipulation"], ["hive", "sightengine"])
        self.assertEqual(report["verdict"], "Manipulated")

    def test_shared_hive_image_and_facial_head_are_one_provider(self):
        hive = detector(ai_generated_score=.99, deepfake_score=.99)
        report = media_report({"hive": hive, "hive_deepfake": {**hive, "shared_request": "hive"}})
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "isolated_manipulation")
        self.assertEqual(signal["independent_provider_count"], 1)
        self.assertEqual(signal["ai_provider_count"], 1)
        self.assertEqual(signal["manipulation_provider_count"], 1)
        self.assertEqual(signal["strong_providers"], {"ai": ["hive"], "manipulation": ["hive"]})
        self.assertEqual(report["analysis_status"], "inconclusive")

    def test_experimental_and_nonvoting_results_cannot_supply_a_signal(self):
        for eligibility in ({"voting_eligible": False}, {"decision_role": "experimental_signal"}):
            with self.subTest(eligibility=eligibility):
                report = media_report({"huggingface": detector(ai_probability=.99, **eligibility),
                                       "sightengine": detector(genai_probability=.01)})
                self.assertEqual(report["media_signal"]["state"], "no_high_signal")
                self.assertEqual(report["media_signal"]["valid_providers"]["ai"], ["sightengine"])

    def test_unavailable_error_disabled_and_partial_do_not_become_no_signal(self):
        for status in ("error", "disabled", "partial", "timeout", "budget_exhausted", "not_configured",
                       "invalid_response", "pending", "no_signal", "aggregate_only"):
            with self.subTest(status=status):
                layer = {"available": True, "status": status, "ai_generated_score": .99}
                report = media_report({"hive": layer})
                self.assertEqual(report["media_signal"]["state"], "unavailable")
                self.assertEqual(report["media_signal"]["independent_provider_count"], 0)
                self.assertEqual(report["provider_coverage"]["hive"]["status"], status)
        self.assertEqual(media_report({})["media_signal"]["state"], "unavailable")
        self.assertEqual(media_report({"hive": {"available": False, "status": "success", "ai_generated_score": .99}})
                         ["media_signal"]["state"], "unavailable")

    def test_missing_status_and_invalid_values_do_not_manufacture_diagnostics(self):
        report = media_report({"hive": {"available": True, "ai_generated_score": .99}})
        self.assertEqual(report["media_signal"]["state"], "unavailable")
        self.assertEqual(report["verdict"], "Suspicious", "Legacy decision remains unchanged")
        for score in (True, "0.99", float("nan"), float("inf"), -1, 2, None):
            with self.subTest(score=score):
                report = media_report({"hive": detector(ai_generated_score=score)})
                self.assertEqual(report["media_signal"]["state"], "unavailable")
                json.dumps(report["media_signal"], allow_nan=False)

    def test_reading_inspection_and_credentials_do_not_create_detector_signals(self):
        forensics = {"ocr": {"status": "no_text", "text": ""},
                     "audio": {"transcription": "", "transcription_detail": {"status": "no_speech"}},
                     "gemini_vision": {"available": True, "status": "success", "ai_probability": .99},
                     "c2pa": {"validation_state": "valid", "generative_ai_flag": True}}
        report = media_report(forensics)
        self.assertEqual(report["media_signal"]["state"], "unavailable")
        self.assertEqual(report["provider_coverage"]["ocr"]["status"], "no_text")
        self.assertEqual(report["provider_coverage"]["transcription"]["status"], "no_speech")
        self.assertEqual(report["verdict"], "AI_Generated", "Existing credential rule is unchanged")

    def test_disagreement_in_one_dimension_does_not_change_existing_other_decision(self):
        report = media_report({"hive": detector(ai_generated_score=.99, deepfake_score=.99),
                               "sightengine": detector(genai_probability=.99, deepfake_probability=.01)})
        self.assertEqual(report["media_signal"]["state"], "disagreement")
        self.assertEqual((report["verdict"], report["analysis_status"]), ("AI_Generated", "partial"))

    def test_legacy_contract_without_new_field_is_not_reinterpreted(self):
        report = media_report({"hive": detector(ai_generated_score=.99)})
        report.pop("media_signal")
        result = forensic_contract(report)
        self.assertNotIn("media_signal", result)
        self.assertEqual(result["veredito_final"], "inconclusivo")


class VideoMediaSignalTests(unittest.IsolatedAsyncioTestCase):
    async def analyze_frames(self, frames, *, audio=None):
        media = ValidatedMedia(b"control", "control.mp4", "video/mp4", "video",
                               {"duration_seconds": 3, "has_audio": audio is not None})
        timestamps = [.3, 1.5, 2.7][:len(frames)]
        with patch("app.services.media_analysis.video_visual_layers", new=AsyncMock(return_value=(
                [(timestamp, b"frame") for timestamp in timestamps], frames))), \
             patch("app.services.media_analysis.video_audio_layers", new=AsyncMock(return_value=audio)):
            return await analyze_media(media)

    async def test_high_on_one_provider_stays_isolated_in_sampled_frames(self):
        frame = {"hive": detector(ai_generated_score=.99)}
        report = await self.analyze_frames([frame] * 3)
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "isolated_ai")
        self.assertEqual(signal["scope"], "sampled_video_frames")
        self.assertEqual(signal["sampled_frames"], 3)
        self.assertEqual(signal["state_counts"], {"isolated_ai": 3})
        self.assertEqual(signal["observed_timestamps_seconds"], [.3, 1.5, 2.7])
        self.assertEqual(signal["independent_provider_count"], 1)
        self.assertEqual(report["flagged_timestamps_seconds"], [])
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["forensics"]["video"]["frames"][0]["media_signal"]["state"], "isolated_ai")
        self.assertIn("sinais isolados", report["summary"])
        self.assertIn("quadros amostrados", report["summary"])
        self.assertIn("não determina a origem do vídeo inteiro", report["summary"])
        self.assertEqual(report["summary"], report["plain_explanation"])
        self.assertEqual(report["summary"], report["whatsapp_share_text"])

    async def test_different_high_providers_at_different_times_do_not_create_consensus(self):
        report = await self.analyze_frames([{"hive": detector(ai_generated_score=.99)},
                                            {"sightengine": detector(genai_probability=.99)}])
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "isolated_ai")
        self.assertEqual(signal["independent_provider_count"], 2)
        self.assertEqual(signal["strong_providers"]["ai"], ["hive", "sightengine"])
        self.assertEqual(signal["state_counts"], {"isolated_ai": 2})
        self.assertEqual([item["independent_provider_count"] for item in signal["observations"]], [1, 1])
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertEqual(report["flagged_timestamps_seconds"], [])

    async def test_same_frame_consensus_preserves_existing_sample_flag(self):
        report = await self.analyze_frames([{"hive": detector(ai_generated_score=.99),
                                             "sightengine": detector(genai_probability=.99)}])
        self.assertEqual(report["media_signal"]["state"], "consensus_ai")
        self.assertEqual(report["flagged_timestamps_seconds"], [.3])
        self.assertEqual((report["verdict"], report["analysis_status"]), ("AI_Generated", "partial"))

    async def test_frame_disagreement_preserved_beside_existing_consensus(self):
        report = await self.analyze_frames([
            {"hive": detector(ai_generated_score=.99), "sightengine": detector(genai_probability=.99)},
            {"hive": detector(ai_generated_score=.99), "sightengine": detector(genai_probability=.01)}])
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "disagreement")
        self.assertEqual(signal["state_counts"], {"consensus_ai": 1, "disagreement": 1})
        self.assertEqual(report["flagged_timestamps_seconds"], [.3])
        self.assertEqual(report["analysis_status"], "partial", "Legacy sampled-frame decision is preserved")

    async def test_face_only_partial_coverage_keeps_counts_statuses_and_reasons(self):
        report = await self.analyze_frames([
            {"sightengine": detector(deepfake_probability=.1)},
            {"sightengine": {"available": False, "status": "timeout", "reason": "Prazo excedido."}}])
        signal = report["media_signal"]
        self.assertEqual(signal["state"], "no_high_signal")
        self.assertEqual(signal["ai_provider_count"], 0)
        self.assertEqual(signal["manipulation_provider_count"], 1)
        self.assertEqual(signal["state_counts"], {"no_high_signal": 1, "unavailable": 1})
        layer = report["provider_coverage"]["sightengine"]
        self.assertEqual(layer["status"], "partial")
        self.assertEqual(layer["frame_status_counts"], {"success": 1, "timeout": 1})
        self.assertEqual(layer["failure_reasons"], ["Prazo excedido."])

    async def test_disabled_video_layers_remain_unavailable_not_no_high_signal(self):
        report = await self.analyze_frames([{"hive": {"available": False, "status": "disabled"}}] * 3)
        self.assertEqual(report["media_signal"]["state"], "unavailable")
        self.assertEqual(report["media_signal"]["state_counts"], {"unavailable": 3})
        self.assertEqual(report["provider_coverage"]["hive"]["status"], "disabled")

    async def test_video_voice_signal_does_not_change_visual_diagnostic(self):
        audio = media_report({"hive": detector(ai_generated_score=.974),
                              "sightengine_audio": {"available": False, "status": "disabled"}}, "audio")
        report = await self.analyze_frames([{"hive": detector(ai_generated_score=.001)}], audio=audio)
        self.assertEqual(report["media_signal"]["state"], "no_high_signal")
        self.assertEqual(report["audio_analysis"]["media_signal"]["state"], "isolated_ai")
        self.assertEqual(report["visual_authenticity_status"], "undetermined")
        self.assertEqual(report["analysis_status"], "inconclusive")
        self.assertIn("Não apareceram sinais fortes nos quadros amostrados", report["summary"])
        self.assertIn("Faixa de áudio: Um detector encontrou sinal de possível fala sintética", report["summary"])
        self.assertIn("não comprova clonagem", report["whatsapp_share_text"])
        self.assertNotRegex(report["summary"], r"Hive|Sightengine|%")

    async def test_content_risk_keeps_qualified_audio_signal_in_api_and_share_summary(self):
        media = ValidatedMedia(b"control", "control.wav", "audio/wav", "audio", {"duration_seconds": 3})
        layers = {"hive": detector(ai_generated_score=.974),
                  "sightengine_audio": {"available": False, "status": "disabled"},
                  "audio": {"transcription": "Faça um Pix para mim.", "content_risk": {"is_scam_pattern": True}}}
        with patch("app.services.media_analysis.audio_layers", new=AsyncMock(return_value=layers)), \
             patch("app.services.media_analysis.extracted_content", new=AsyncMock(return_value={"veracity_status": "unverified"})):
            report = await analyze_media(media)
        self.assertIn("pedido financeiro suspeito", report["summary"])
        self.assertIn("possível fala sintética", report["summary"])
        self.assertIn("ainda não confirma a origem da voz", report["summary"])
        self.assertEqual(report["summary"], report["plain_explanation"])
        self.assertEqual(report["summary"], report["whatsapp_share_text"])
        self.assertEqual((report["verdict"], report["analysis_status"], report["score"]),
                         ("Suspicious", "inconclusive", 50))

    def test_video_helper_bounds_observations_and_does_not_reinterpret_legacy_frames(self):
        report = media_report({"hive": detector(ai_generated_score=.99)})
        signal = video_media_signal([report] * 20, list(range(20)))
        self.assertEqual(signal["sampled_frames"], 12)
        self.assertEqual(len(signal["observations"]), 12)
        legacy = {key: value for key, value in report.items() if key != "media_signal"}
        self.assertEqual(video_media_signal([legacy], [1])["state"], "unavailable")
        for timestamp in (True, float("nan"), float("inf"), -1, 121):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(video_media_signal([report], [timestamp])["state"], "unavailable")
        json.dumps(signal, allow_nan=False)
