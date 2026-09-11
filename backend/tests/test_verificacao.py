import io
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from helpers import app, fake_user, override_auth_and_db, FakeSession, ScalarResult


class VerificacaoDemonstracaoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_capturar_selo_e_detectar_adulteracao(self):
        # 1. Captura imagem original
        original_image = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00ORIGINAL_PHOTO_PIXELS_ABC_123"
        
        resp_cap = self.client.post(
            "/api/capturar/selo",
            files={"file": ("foto_demonstracao.jpg", original_image, "image/jpeg")}
        )
        self.assertEqual(resp_cap.status_code, 200)
        cap_data = resp_cap.json()
        self.assertTrue(cap_data["autentico"])
        self.assertEqual(cap_data["status"], "SEALED")
        file_hash = cap_data["file_hash_sha256"]

        # 2. Verifica foto original -> Deve passar (mock retornando o selo recém-criado)
        self.db.execute_results = [ScalarResult(self.db.added[0])]
        resp_ver = self.client.post(
            "/api/verificar/selo",
            files={"file": ("foto_demonstracao.jpg", original_image, "image/jpeg")}
        )
        self.assertEqual(resp_ver.status_code, 200)
        ver_data = resp_ver.json()
        self.assertTrue(ver_data["autentico"])
        self.assertEqual(ver_data["status"], "VALID")

        # 3. Altera 1 byte da foto (simula adulteração de pixel no Photoshop) -> Deve falhar
        self.db.execute_results = [ScalarResult(None)]
        tampered_image = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00TAMPERED_PHOTO_PIXELS_XYZ_999"
        resp_tampered = self.client.post(
            "/api/verificar/selo",
            files={"file": ("foto_demonstracao.jpg", tampered_image, "image/jpeg")}
        )
        self.assertEqual(resp_tampered.status_code, 200)
        tamp_data = resp_tampered.json()
        self.assertFalse(tamp_data["autentico"])
        self.assertEqual(tamp_data["status"], "TAMPERED_OR_UNKNOWN")

    def test_audio_rapido_demonstracao(self):
        sample_audio = b"RIFF....WAVEfmt ....fake_audio_clonado_data"
        resp = self.client.post(
            "/api/verificar/audio-rapido",
            files={"file": ("golpe_parente_clonado.wav", sample_audio, "audio/wav")}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("verdict", data)
        self.assertIn("confidence", data)
        self.assertIn("short_explanation", data)
        self.assertIn("tempo_processamento_ms", data)
        self.assertEqual(data["verdict"], "sintetica")

    def test_verificar_completo_pipeline(self):
        sample_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png"
        resp = self.client.post(
            "/api/verificar/completo",
            files={"file": ("documento.png", sample_image, "image/png")}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("metadata", data)
        self.assertIn("c2pa", data)
        self.assertIn("deteccao_ia", data)
        self.assertIn("contexto", data)
        self.assertIn("veredito", data)

    def test_exportar_relatorio_pdf(self):
        sample_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_evidence"
        resp = self.client.post(
            "/api/verificar/relatorio-pdf",
            files={"file": ("evidencia.png", sample_image, "image/png")}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
