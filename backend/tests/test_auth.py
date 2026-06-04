import unittest

from fastapi.testclient import TestClient

from helpers import app, fake_user, override_auth_and_db, FakeSession


class AuthIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = fake_user()
        self.db = FakeSession()
        override_auth_and_db(self.user, self.db)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_me_returns_current_user(self):
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user.email)
        self.assertEqual(response.json()["name"], self.user.name)

    def test_health_endpoint_returns_ok_with_security_headers(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
