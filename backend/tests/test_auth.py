import unittest

from fastapi.testclient import TestClient

from helpers import app, fake_user, override_auth_and_db, FakeSession, ScalarResult
from app.core.security import create_refresh_token


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
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_refresh_rotates_http_only_cookie_tokens(self):
        self.db.execute_results = [ScalarResult(self.user)]
        self.client.cookies.set(
            "verifai_refresh",
            create_refresh_token(str(self.user.id)),
            path="/api/auth/refresh",
        )

        response = self.client.post("/api/auth/refresh")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access_token", response.json())
        self.assertNotIn("refresh_token", response.json())
        cookies = response.headers.get_list("set-cookie")
        from app.api.auth import _COOKIE_SAME_SITE
        self.assertTrue(any("verifai_access=" in cookie and "HttpOnly" in cookie and f"SameSite={_COOKIE_SAME_SITE}".lower() in cookie.lower() for cookie in cookies))
        self.assertTrue(any("verifai_refresh=" in cookie and "HttpOnly" in cookie and "Path=/api/auth/refresh" in cookie for cookie in cookies))

    def test_logout_clears_auth_cookies(self):
        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 204)
        cookies = response.headers.get_list("set-cookie")
        self.assertTrue(any("verifai_access=" in cookie and "Max-Age=0" in cookie for cookie in cookies))
        self.assertTrue(any("verifai_refresh=" in cookie and "Max-Age=0" in cookie for cookie in cookies))


if __name__ == "__main__":
    unittest.main()
