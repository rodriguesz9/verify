import argparse
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.run_offline_tests import configure_test_environment, postgres_test_url


class OfflineRunnerTests(unittest.TestCase):
    def test_inherited_credentials_and_database_are_not_reused(self):
        inherited = {"DATABASE_URL": "postgresql://private", "TEST_DATABASE_URL": "postgresql://private",
            "GEMINI_API_KEY": "private", "UNKNOWN_API_KEY": "private", "OPENROUTER_API_KEY": "private",
            "HUGGINGFACE_API_TOKEN": "private", "SIGHTENGINE_API_SECRET": "private",
            "HMAC_SECRET_KEY": "private", "JWT_SECRET": "private", "APP_ENV": "production",
            "WHATSAPP_HISTORY_ENABLED": "true", "WHATSAPP_HASH_SECRET": "private"}
        with patch.dict(os.environ, inherited):
            configure_test_environment(Path("/tmp/disposable-test-directory"))
            self.assertEqual(os.environ["DATABASE_URL"], "sqlite+aiosqlite:////tmp/disposable-test-directory/app-test.db")
            self.assertEqual(os.environ["TEST_DATABASE_URL"], "sqlite+aiosqlite:////tmp/disposable-test-directory/query-test.db")
            for key in ("GEMINI_API_KEY", "UNKNOWN_API_KEY", "OPENROUTER_API_KEY", "HUGGINGFACE_API_TOKEN", "SIGHTENGINE_API_SECRET"):
                self.assertEqual(os.environ[key], "")
            self.assertEqual(os.environ["WHATSAPP_HISTORY_ENABLED"], "false")
            self.assertEqual(os.environ["WHATSAPP_HASH_SECRET"], "")
            self.assertGreaterEqual(len(os.environ["JWT_SECRET"]), 32)
            self.assertNotEqual(os.environ["JWT_SECRET"], os.environ["HMAC_SECRET_KEY"])

    def test_postgres_opt_in_refuses_remote_or_non_test_database(self):
        valid = "postgresql+asyncpg://test:fake@127.0.0.1:55436/verify_ci_test"
        self.assertEqual(postgres_test_url(valid), valid)
        for value in ("not-a-url", "postgresql://test:fake@localhost/verify_test",
                      "postgresql+asyncpg://test:fake@localhost/production",
                      "postgresql+asyncpg://test:fake@remote.example/verify_test",
                      valid + "?host=remote.example"):
            with self.subTest(url_kind=value.split(":")[0]), self.assertRaises(argparse.ArgumentTypeError) as error:
                postgres_test_url(value)
            self.assertNotIn("fake", str(error.exception))
            self.assertNotIn("remote.example", str(error.exception))
