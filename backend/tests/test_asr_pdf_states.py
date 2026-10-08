"""PDF projection of ASR states; simulated controls, not detector accuracy."""

import copy
import hashlib
import subprocess
import unittest
from helpers import valid_wav
from app.services.evidence_policy import media_report, forensic_contract
from app.services.pdf_report_service import generate_forensic_pdf


def pending_pdf_control(status="pending", kind="audio"):
    layer = {"transcription": "", "transcription_detail": {"status": status, "provider": "assemblyai"}}
    audio = media_report({"audio": layer}, "audio")
    report = audio if kind == "audio" else {**media_report({}, "video"), "audio_analysis": audio,
        "media_details": {"has_audio": True}, "visual_authenticity_status": "undetermined",
        "visual_analysis_status": "inconclusive"}
    return {**forensic_contract(report), "filename": "controle-simulado-pendente.wav" if kind == "audio" else "controle-simulado-pendente.mp4",
            "file_hash_sha256": hashlib.sha256(valid_wav()).hexdigest(),
            "analyzed_at": "2026-10-07T17:00:00+00:00"}


class AsrPdfStatesTests(unittest.TestCase):
    def test_pdf_labels_are_portuguese_and_do_not_turn_asr_state_into_voice_origin(self):
        for state, label in (("pending", "Pendente"), ("in_progress", "Em processamento"),
                             ("blocked_uncertain", "Estado não confirmado"),
                             ("blocked_expired", "Acompanhamento encerrado"),
                             ("capacity_exceeded", "Serviço ocupado")):
            for kind in ("audio", "video"):
                with self.subTest(state=state, kind=kind):
                    report = pending_pdf_control(state, kind)
                    before = copy.deepcopy(report)
                    data = generate_forensic_pdf(report, report["filename"], report["file_hash_sha256"])
                    text = subprocess.run(["pdftotext", "-", "-"], input=data, capture_output=True, check=True).stdout.decode()
                    self.assertIn(label, text)
                    if "_" in state:
                        self.assertNotIn(state, text)
                    self.assertNotIn("Voz humana", text)
                    self.assertNotIn("Voz clonada", text)
                    self.assertNotIn("private-fixture-job", text)
                    self.assertNotIn("cdn.assemblyai.com", text)
                    self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
