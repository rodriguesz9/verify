"""Offline session/Google-linking regressions; never contact Google or a DB."""
import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from helpers import fake_user, FakeSession, ScalarResult
from app.api import auth as auth_api
from app.core import auth as auth_core
from app.core.rate_limit import limiter


class AuthSession(FakeSession):
    def __init__(self, execute_results=None):
        super().__init__(execute_results)
        self.executions = 0

    async def execute(self, statement):
        self.executions += 1
        return await super().execute(statement)

    async def refresh(self, instance):
        # Only simulate defaults for newly inserted accounts, not existing users.
        if instance in self.added:
            instance.id = instance.id or uuid.uuid4()
            instance.is_active = True


def google_claims(**changes):
    claims = {
        "sub": "google-test-subject-001",
        "email": "owner@gmail.com",
        "email_verified": True,
        "name": "Owner",
        "picture": "https://example.test/avatar.png",
    }
    claims.update(changes)
    return claims


class AuthReleaseSecurityTests(unittest.TestCase):
    def setUp(self):
        # Test the production auth router in isolation: cumulative request-budget
        # middleware limits belong to their own tests, not these claim subcases.
        self.app = FastAPI()
        self.app.state.limiter = limiter
        self.app.include_router(auth_api.router, prefix="/api")
        self.client = TestClient(self.app)
        self.user = fake_user(
            email="owner@gmail.com", google_id=None, hashed_password="legacy-hash",
            last_login=None,
        )
        self.db = AuthSession()
        async def db_override():
            yield self.db
        self.app.dependency_overrides[auth_api.get_db] = db_override
        limiter.reset()

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()
        limiter.reset()

    def assert_refused_without_mutation(self, response, previous_user):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get_list("set-cookie"), [])
        self.assertEqual(self.db.commits, 0)
        self.assertEqual(self.db.added, [])
        self.assertEqual(vars(self.user), previous_user)

    def google_post(self, claims):
        with patch.object(auth_api, "verify_google_id_token", return_value=claims):
            return self.client.post("/api/auth/google", json={"id_token": "offline-token-only"})

    def assert_session_started(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": "Sessão iniciada."})
        cookies = response.headers.get_list("set-cookie")
        self.assertTrue(any("verifai_access=" in item and "HttpOnly" in item for item in cookies))
        self.assertTrue(any("verifai_refresh=" in item and "HttpOnly" in item for item in cookies))

    def test_password_login_inactive_account_gets_no_session_or_last_login_change(self):
        self.user.is_active = False
        self.db.execute_results = [ScalarResult(self.user)]
        previous = vars(self.user).copy()
        with patch.object(auth_api, "verify_password", return_value=True) as verify:
            response = self.client.post("/api/auth/login", json={
                "email": "owner@gmail.com", "password": "correct-password",
            })
        self.assert_refused_without_mutation(response, previous)
        verify.assert_not_called()

    def test_all_failed_password_logins_have_the_same_public_error(self):
        errors = []
        for account, valid_password in [(None, False), (self.user, False),
                (fake_user(hashed_password=None, is_active=True), False),
                (fake_user(hashed_password="legacy-hash", is_active=False), True)]:
            with self.subTest(account_exists=account is not None, valid_password=valid_password):
                limiter.reset()
                self.db.execute_results = [ScalarResult(account)]
                previous = vars(self.user).copy()
                with patch.object(auth_api, "verify_password", return_value=valid_password):
                    response = self.client.post("/api/auth/login", json={
                        "email": "owner@gmail.com", "password": "password",
                    })
                self.assert_refused_without_mutation(response, previous)
                errors.append(response.json())
        self.assertEqual(errors, [{"detail": "E-mail ou senha inválidos."}] * len(errors))

    def test_valid_legacy_password_login_still_issues_session(self):
        self.db.execute_results = [ScalarResult(self.user)]
        with patch.object(auth_api, "verify_password", return_value=True) as verify:
            response = self.client.post("/api/auth/login", json={
                "email": "OWNER@GMAIL.COM", "password": "legacy-password",
            })
        self.assert_session_started(response)
        verify.assert_called_once_with("legacy-password", "legacy-hash")
        self.assertIsNotNone(self.user.last_login)
        self.assertEqual(self.db.commits, 1)

    def test_google_email_verified_is_strict_boolean_true(self):
        for verified in [None, False, "true", "false", 1, 0, [], {}]:
            with self.subTest(verified=verified):
                previous = vars(self.user).copy()
                response = self.google_post(google_claims(email_verified=verified))
                self.assert_refused_without_mutation(response, previous)
                self.assertEqual(self.db.executions, 0)

    def test_google_missing_email_verified_is_rejected_before_lookup(self):
        claims = google_claims()
        claims.pop("email_verified")
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(self.google_post(claims), previous)
        self.assertEqual(self.db.executions, 0)

    def test_google_invalid_subject_is_rejected_before_lookup(self):
        for subject in [None, "", " ", "id with space", "subject\n", "ü", "a" * 256,
                        False, 1, [], {}]:
            with self.subTest(subject=subject):
                previous = vars(self.user).copy()
                response = self.google_post(google_claims(sub=subject))
                self.assert_refused_without_mutation(response, previous)
                self.assertEqual(self.db.executions, 0)

    def test_google_invalid_email_or_payload_is_rejected_before_lookup(self):
        for claims in [None, [], "payload", google_claims(email=None), google_claims(email={}),
                google_claims(email="bad-address"), google_claims(email="a" * 255 + "@gmail.com")]:
            with self.subTest(claims=claims):
                previous = vars(self.user).copy()
                self.assert_refused_without_mutation(self.google_post(claims), previous)
                self.assertEqual(self.db.executions, 0)

    def test_google_verifier_failure_does_not_expose_exception_or_mutate(self):
        previous = vars(self.user).copy()
        with patch.object(auth_api, "verify_google_id_token", side_effect=ValueError("private-token-debug")):
            response = self.client.post("/api/auth/google", json={"id_token": "offline-token-only"})
        self.assert_refused_without_mutation(response, previous)
        self.assertNotIn("private-token-debug", response.text)
        self.assertEqual(self.db.executions, 0)

    def test_google_inactive_subject_match_does_not_start_session(self):
        self.user.google_id = "google-test-subject-001"
        self.user.is_active = False
        self.db.execute_results = [ScalarResult(values=[self.user])]
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(self.google_post(google_claims()), previous)
        self.assertEqual(self.db.executions, 1)

    def test_google_inactive_email_match_is_not_linked(self):
        self.user.is_active = False
        self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(self.google_post(google_claims()), previous)

    def test_google_conflicting_existing_subject_is_not_replaced(self):
        self.user.google_id = "different-subject"
        self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(self.google_post(google_claims()), previous)

    def test_google_ambiguous_legacy_subject_is_rejected(self):
        self.user.google_id = "google-test-subject-001"
        other_user = fake_user(google_id=self.user.google_id, last_login=None)
        self.db.execute_results = [ScalarResult(values=[self.user, other_user])]
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(self.google_post(google_claims()), previous)
        self.assertIsNone(other_user.last_login)

    def test_google_external_email_cannot_implicitly_link_existing_account(self):
        self.user.email = "owner@example.test"
        self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
        previous = vars(self.user).copy()
        self.assert_refused_without_mutation(
            self.google_post(google_claims(email=self.user.email)), previous)

    def test_google_empty_or_non_string_hd_does_not_authorize_email_linking(self):
        self.user.email = "owner@example.test"
        for hosted_domain in [None, "", " ", True, 1, [], {}]:
            with self.subTest(hosted_domain=hosted_domain):
                self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
                previous = vars(self.user).copy()
                self.assert_refused_without_mutation(self.google_post(
                    google_claims(email=self.user.email, hd=hosted_domain)), previous)

    def test_google_gmail_may_link_active_unbound_account(self):
        self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
        response = self.google_post(google_claims(email="OWNER@GMAIL.COM"))
        self.assert_session_started(response)
        self.assertEqual(self.user.google_id, "google-test-subject-001")
        self.assertEqual(self.user.hashed_password, "legacy-hash")
        self.assertEqual(self.db.commits, 1)
        self.assertEqual(self.db.added, [])

    def test_google_signed_workspace_hd_may_link_active_unbound_account(self):
        self.user.email = "owner@example.test"
        self.db.execute_results = [ScalarResult(), ScalarResult(self.user)]
        response = self.google_post(google_claims(email=self.user.email, hd="example.test"))
        self.assert_session_started(response)
        self.assertEqual(self.user.google_id, "google-test-subject-001")
        self.assertEqual(self.db.commits, 1)

    def test_google_existing_subject_login_preserves_identity_despite_changed_email(self):
        self.user.email = "legacy@example.test"
        self.user.google_id = "google-test-subject-001"
        self.db.execute_results = [ScalarResult(values=[self.user])]
        response = self.google_post(google_claims(email="changed@example.test"))
        self.assert_session_started(response)
        self.assertEqual(self.user.email, "legacy@example.test")
        self.assertEqual(self.user.google_id, "google-test-subject-001")
        self.assertEqual(self.db.executions, 1)

    def test_google_new_external_email_creates_subject_bound_account(self):
        self.db.execute_results = [ScalarResult(), ScalarResult()]
        response = self.google_post(google_claims(email="new@example.test", name=None, picture={}))
        self.assert_session_started(response)
        self.assertEqual(len(self.db.added), 1)
        new_user = self.db.added[0]
        self.assertEqual(new_user.google_id, "google-test-subject-001")
        self.assertEqual(new_user.email, "new@example.test")
        self.assertEqual(new_user.name, "new")
        self.assertIsNone(new_user.avatar_url)
        self.assertIsNone(new_user.hashed_password)


class GoogleVerifierReleaseSecurityTests(unittest.TestCase):
    def test_missing_google_audience_fails_without_network(self):
        for client_id in ["", " "]:
            with self.subTest(client_id=client_id):
                with patch.object(auth_core, "_GOOGLE_CLIENT_ID", client_id), \
                        patch.object(auth_core.google_id_token, "verify_oauth2_token") as verifier:
                    with self.assertRaises(HTTPException) as failure:
                        auth_core.verify_google_id_token("offline-token-only")
                self.assertEqual(failure.exception.status_code, 401)
                verifier.assert_not_called()

    def test_google_library_receives_configured_audience(self):
        with patch.object(auth_core, "_GOOGLE_CLIENT_ID", "app-test-client-id"), \
                patch.object(auth_core.google_requests, "Request", return_value="mock-transport"), \
                patch.object(auth_core.google_id_token, "verify_oauth2_token", return_value=google_claims()) as verifier:
            result = auth_core.verify_google_id_token("offline-token-only")
        verifier.assert_called_once_with("offline-token-only", "mock-transport", "app-test-client-id")
        self.assertEqual(result["sub"], "google-test-subject-001")

    def test_verifier_exception_detail_stays_private(self):
        with patch.object(auth_core, "_GOOGLE_CLIENT_ID", "app-test-client-id"), \
                patch.object(auth_core.google_requests, "Request", return_value="mock-transport"), \
                patch.object(auth_core.google_id_token, "verify_oauth2_token", side_effect=ValueError("private-token-debug")):
            with self.assertRaises(HTTPException) as failure:
                auth_core.verify_google_id_token("offline-token-only")
        self.assertEqual(failure.exception.status_code, 401)
        self.assertNotIn("private-token-debug", failure.exception.detail)


if __name__ == "__main__":
    unittest.main()
