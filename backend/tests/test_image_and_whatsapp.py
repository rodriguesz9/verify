import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from helpers import app, fake_user, override_auth_and_db, FakeSession
from app.services.metadata_service import _scan_for_ai_signatures, _scan_for_editing_signatures
from app.api.whatsapp import format_whatsapp_response


class ImageForensicsAndWhatsAppTests(unittest.TestCase):
    def setUp(self):
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_photoshop_is_not_classified_as_ai_signature(self):
        metadata_photoshop = {
            "Software": "Adobe Photoshop 25.0 (Windows)",
            "CreatorTool": "Adobe Photoshop CC 2024",
            "Make": "Canon",
            "Model": "EOS R6"
        }
        ai_sigs = _scan_for_ai_signatures(metadata_photoshop)
        edit_sigs = _scan_for_editing_signatures(metadata_photoshop)

        self.assertEqual(ai_sigs, [], "Photoshop não pode ser considerado assinatura de IA generativa.")
        self.assertIn("photoshop", edit_sigs, "Photoshop deve ser reconhecido como software convencional de edição.")

    def test_midjourney_is_correctly_classified_as_ai(self):
        metadata_midjourney = {
            "Software": "Midjourney v6.0",
            "Description": "Prompt: cyberpunk city in rain"
        }
        ai_sigs = _scan_for_ai_signatures(metadata_midjourney)
        self.assertIn("midjourney", ai_sigs)

    def test_whatsapp_response_formatting_for_seniors(self):
        fake_report = {
            "verdict": "Scam",
            "score": 15,
            "summary": "Mensagem fingindo ser do banco pedindo atualização de chave Pix.",
            "plain_explanation": "Golpistas criam mensagens falsas de banco para roubar seu dinheiro.",
            "elderly_tip": "O banco nunca manda mensagem pedindo para clicar em link e recadastrar chave Pix.",
            "red_flags": ["Pedido urgente de recadastramento", "Link suspeito não oficial"]
        }
        msg = format_whatsapp_response(fake_report, "Atualize seu Pix agora")
        self.assertIn("ALERTA DE GOLPE", msg)
        self.assertIn("DICA DE SEGURANÇA", msg)
        self.assertIn("O banco nunca manda mensagem", msg)
        self.assertIn("https://verify.vercel.app", msg)

    def test_whatsapp_webhook_empty_payload(self):
        resp = self.client.post("/api/whatsapp/webhook", json={"message": ""})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ignored")

    def test_whatsapp_simulate_endpoint(self):
        fake_pipeline_result = {
            "report": {
                "verdict": "Authentic",
                "score": 90,
                "summary": "Vacinação contra gripe inicia segunda-feira nos postos de saúde.",
                "plain_explanation": "Notícia confirmada pelo Ministério da Saúde.",
                "elderly_tip": "Procure a UBS mais próxima levando sua carteira de vacinação.",
                "red_flags": []
            }
        }
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock(return_value=fake_pipeline_result)):
            resp = self.client.post(
                "/api/whatsapp/simulate",
                json={"message": "Inicia vacinação contra gripe na próxima semana"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("whatsapp_reply", data)
            self.assertIn("VERDADEIRO", data["whatsapp_reply"])


if __name__ == "__main__":
    unittest.main()
