"""PDF must not turn acoustic indications into a visual-origin verdict."""
import subprocess
import unittest

from app.services.pdf_report_service import generate_forensic_pdf


def video_report(**overrides):
    return {
        "content_type": "video", "verdict": "AI_Generated", "score": 20,
        "analysis_status": "partial", "authenticity_status": "ai_indications",
        "visual_authenticity_status": "undetermined", "visual_analysis_status": "inconclusive",
        "visual_detector_disagreement": False, "media_details": {"has_audio": True},
        "summary": "Controle fictício: apenas a faixa de áudio tem sinais concordantes.",
        "audio_analysis": {"authenticity_status": "ai_indications", "analysis_status": "partial",
            "provider_coverage": {"hive": {"status": "success", "ai_score": .94},
                "transcription": {"status": "success", "decision_role": "transcription_only"}}},
        **overrides,
    }


class PdfDimensionTests(unittest.TestCase):
    def extract(self, report):
        data = generate_forensic_pdf(report, "controle-ficticio.mp4", "a" * 64)
        self.assertTrue(data.startswith(b"%PDF"))
        return subprocess.run(["pdftotext", "-", "-"], input=data,
            capture_output=True, check=True).stdout.decode("utf-8")

    def test_audio_only_keeps_visual_undetermined_and_audio_coverage(self):
        text = self.extract(video_report())
        self.assertIn("RESULTADO DAS CAMADAS", text)
        self.assertIn("INDÍCIOS DE FALA SINTÉTICA", text)
        self.assertIn("Origem dos quadros visuais: Origem indeterminada", text)
        self.assertIn("Origem da faixa de áudio: Indícios de possível fala sintética", text)
        self.assertIn("Áudio/hive", text)
        self.assertIn("sinal de fala sintética: 0.94", text)
        self.assertIn("Sinais da voz não se aplicam à origem das imagens", text)

    def test_no_audio_overrides_contradictory_legacy_audio_fields(self):
        text = self.extract(video_report(media_details={"has_audio": False}))
        self.assertIn("Faixa de áudio: não existe neste vídeo", text)
        self.assertNotIn("Origem da faixa de áudio: Indícios", text)
        self.assertNotIn("Áudio/hive", text)

    def test_legacy_overall_status_does_not_create_visual_evidence(self):
        report = video_report()
        report.pop("visual_authenticity_status")
        report.pop("visual_analysis_status")
        text = self.extract(report)
        self.assertIn("Origem visual não separada neste relatório legado", text)
        self.assertNotIn("Origem dos quadros visuais: Indícios", text)

    def test_failed_audio_does_not_present_legacy_positive_as_success(self):
        text = self.extract(video_report(audio_analysis={"authenticity_status": "ai_indications",
            "analysis_status": "inconclusive", "detector_disagreement": True}))
        self.assertIn("Origem da faixa de áudio: Não determinada", text)
        self.assertNotIn("Origem da faixa de áudio: Indícios", text)
        self.assertIn("detectores da faixa de áudio discordaram", text)
