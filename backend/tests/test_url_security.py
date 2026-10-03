import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.services.public_fetch import _resolve_public_host, _validate_public_url


class UrlSecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_localhost_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            _resolve_public_host("localhost")
        self.assertEqual(error.exception.status_code, 400)

    def test_private_address_is_rejected(self):
        result = [(None, None, None, None, ("127.0.0.1", 0))]
        with patch("app.services.public_fetch.socket.getaddrinfo", return_value=result):
            with self.assertRaises(HTTPException) as error:
                _resolve_public_host("internal.example")
        self.assertEqual(error.exception.status_code, 400)

    async def test_url_with_credentials_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            await _validate_public_url("https://user:password@example.com/private")
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
