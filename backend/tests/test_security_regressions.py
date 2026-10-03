"""Offline controls for public fetching, webhook auth and admission budgets."""
import asyncio
import base64
import hashlib
import os
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from helpers import app, valid_png, valid_wav
from app.core.request_budget import RequestBudgetMiddleware
from app.services.public_fetch import fetch_public_resource, _validate_public_url
from app.services.whatsapp_security import ReceiptGuard, receipts
from app.api.whatsapp import _hash_sender
from app.core.security import decode_token
from jose import jwt, JWTError


class TokenConfigurationTests(unittest.TestCase):
    def test_publicly_known_fallback_cannot_forge_a_session(self):
        token = jwt.encode({"sub": "fixture", "type": "access"}, "change_me_please_32_chars_minimum!", algorithm="HS256")
        with self.assertRaises(JWTError):
            decode_token(token)

    def test_production_refuses_empty_signing_secret(self):
        env = dict(os.environ, APP_ENV="production", JWT_SECRET="",
                   PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        result = subprocess.run(
            [sys.executable, "-c", "import app.core.security"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Production requires", result.stderr)


class PublicFetchTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_reserved_multicast_and_invalid_urls_are_rejected(self):
        urls = [
            "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/", "http://[::1]/", "http://[fe80::1]/",
            "http://224.0.0.1/", "http://[ff02::1]/",
            "http://[2002:0a00:0001::]/", "https://example.com:8000/",
            "ftp://example.com/", "https://user:password@example.com/",
            "https://example.com/\nsecret", "https://[fe80::1%25eth0]/",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(HTTPException):
                await _validate_public_url(url)

    async def test_dns_rebinding_is_pinned_without_disabling_tls(self):
        requests = []
        async def handle(transport, request):
            requests.append(request)
            return httpx.Response(200, headers={"Content-Type": "text/html"}, stream=httpx.ByteStream(b"<p>ok</p>"))
        public = [(2, 1, 6, "", ("93.184.215.14", 0))]
        private = [(2, 1, 6, "", ("127.0.0.1", 0))]
        with (
            patch("app.services.public_fetch.socket.getaddrinfo", side_effect=[public, private]) as dns,
            patch.object(httpx.AsyncHTTPTransport, "handle_async_request", handle),
        ):
            result = await fetch_public_resource(
                "https://example.com/news?a=1&b=2", max_bytes=1024,
                allowed_types={"text/html"},
            )
        self.assertEqual(dns.call_count, 1)
        self.assertEqual(requests[0].url.host, "93.184.215.14")
        self.assertEqual(requests[0].headers["Host"], "example.com")
        self.assertEqual(requests[0].extensions["sni_hostname"], "example.com")
        self.assertEqual(result.final_url, "https://example.com/news?a=1&b=2")

    async def test_mixed_public_and_private_dns_is_rejected_before_connecting(self):
        addresses = [(2, 1, 6, "", ("93.184.215.14", 0)), (2, 1, 6, "", ("10.0.0.1", 0))]
        with patch("app.services.public_fetch.socket.getaddrinfo", return_value=addresses), patch.object(
            httpx.AsyncHTTPTransport, "handle_async_request", new=AsyncMock()
        ) as network:
            with self.assertRaises(HTTPException) as error:
                await fetch_public_resource("https://example.com", max_bytes=1024)
        self.assertEqual(error.exception.status_code, 400)
        network.assert_not_awaited()

    async def test_redirect_to_private_ip_is_rejected_before_second_request(self):
        async def handle(transport, request):
            return httpx.Response(302, headers={"location": "http://169.254.169.254/"}, stream=httpx.ByteStream(b""))
        with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", handle):
            with self.assertRaises(HTTPException) as error:
                await fetch_public_resource("https://8.8.8.8", max_bytes=1024, max_redirects=5)
        self.assertEqual(error.exception.status_code, 400)

    async def test_download_limits_compression_and_content_type(self):
        cases = [
            ({"content-length": "2048"}, b"", 413),
            ({}, b"x" * 1025, 413),
            ({"content-encoding": "gzip"}, b"small-compressed-bomb", 415),
            ({"content-type": "application/octet-stream"}, b"binary", 415),
        ]
        for headers, data, code in cases:
            with self.subTest(headers=headers):
                async def handle(transport, request):
                    return httpx.Response(200, headers=headers, stream=httpx.ByteStream(data))
                with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", handle):
                    with self.assertRaises(HTTPException) as error:
                        await fetch_public_resource(
                            "https://8.8.8.8", max_bytes=1024,
                            allowed_types={"", "text/html"},
                        )
                self.assertEqual(error.exception.status_code, code)

    async def test_total_timeout_and_internal_error_details_are_not_exposed(self):
        async def slow(transport, request):
            await asyncio.sleep(.05)
        with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", slow):
            with self.assertRaises(HTTPException) as error:
                await fetch_public_resource("https://8.8.8.8", max_bytes=1024, total_timeout=.01)
        self.assertEqual(error.exception.status_code, 504)
        async def fail(transport, request):
            raise httpx.ConnectError("private-network-name-and-sensitive-query")
        with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", fail):
            with self.assertRaises(HTTPException) as error:
                await fetch_public_resource("https://8.8.8.8", max_bytes=1024)
        self.assertNotIn("private-network", error.exception.detail)


class WebhookSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {
            "WHATSAPP_BOT_ENABLED": "true", "WHATSAPP_WEBHOOK_SECRET": "s" * 40,
            "WHATSAPP_HISTORY_ENABLED": "false",
        })
        self.env.start()
        receipts._items.clear()
        self.headers = {"X-Verify-Webhook-Secret": "s" * 40}

    def tearDown(self):
        self.env.stop()
        receipts._items.clear()

    def send(self, body, **kwargs):
        return self.client.post("/api/whatsapp/webhook", json=body, headers=self.headers, **kwargs)

    def test_disabled_unconfigured_and_wrong_secret_never_call_analysis(self):
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock()) as pipeline:
            self.assertEqual(self.client.post("/api/whatsapp/webhook", json={}).status_code, 401)
            with patch.dict(os.environ, {"WHATSAPP_WEBHOOK_SECRET": ""}):
                self.assertEqual(self.send({}).status_code, 503)
            with patch.dict(os.environ, {"WHATSAPP_BOT_ENABLED": "false"}):
                self.assertEqual(self.send({}).status_code, 503)
        pipeline.assert_not_awaited()

    def test_invalid_payloads_return_400_or_422_not_500(self):
        for body in ([], "message", {"data": []}, {"message": []},
                     {"message": "x" * 5001}, {"want_voice_reply": "false"},
                     {"data": {"key": {"fromMe": "false"}}}):
            with self.subTest(body_type=type(body).__name__):
                self.assertEqual(self.send(body).status_code, 422)
        response = self.client.post("/api/whatsapp/webhook", content="{", headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_self_messages_and_other_events_are_ignored(self):
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock()) as pipeline:
            for body in (
                {"event": "SEND_MESSAGE", "message": "Mensagem do próprio bot"},
                {"data": {"key": {"fromMe": True}, "message": {"conversation": "Mensagem do bot"}}},
            ):
                self.assertEqual(self.send(body).json(), {"status": "ignored", "reply": ""})
        pipeline.assert_not_awaited()

    def test_repeated_message_id_does_not_spend_twice(self):
        body = {"event": "messages.upsert", "instance": "test", "data": {
            "key": {"id": "replay-1", "remoteJid": "fixture@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "Texto de controle fictício"},
        }}
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock(return_value={"report": {"verdict": "Suspicious"}})) as pipeline:
            self.assertEqual(self.send(body).json()["status"], "success")
            self.assertEqual(self.send(body).json()["status"], "duplicate")
        self.assertEqual(pipeline.await_count, 1)

    def test_failed_message_can_be_retried(self):
        body = {"message_id": "retry-1", "message": "Texto fictício com falha"}
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock(side_effect=HTTPException(503, "fixture"))):
            self.assertEqual(self.send(body).status_code, 503)
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock(return_value={"report": {}})):
            self.assertEqual(self.send(body).json()["status"], "success")

    def test_base64_image_and_audio_are_actual_bytes_not_send_media_urls(self):
        for field, data, mimetype in (
            ("imageMessage", valid_png(), "image/png"),
            ("audioMessage", valid_wav(), "audio/wav"),
        ):
            with self.subTest(field=field), patch(
                "app.api.whatsapp.analyze_validated_media", new=AsyncMock(return_value={"verdict": "Suspicious", "analysis_status": "inconclusive"})
            ) as analyzer, patch("app.api.whatsapp.download_media", new=AsyncMock()) as download:
                body = {"data": {"base64": base64.b64encode(data).decode(), "message": {
                    field: {"mimetype": mimetype, "caption": "controle fictício"}
                }}}
                response = self.send(body)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(analyzer.call_args.args[0].data, data)
                download.assert_not_awaited()

    def test_video_and_audio_mime_urls_use_media_pipeline(self):
        for mimetype in ("video/mp4", "audio/mpeg"):
            with self.subTest(mimetype=mimetype), patch(
                "app.api.whatsapp.analyze_media", new=AsyncMock(return_value={"verdict": "Suspicious"})
            ) as media, patch("app.api.whatsapp.run_pipeline", new=AsyncMock()) as text:
                response = self.send({"media_url": "https://example.com/fixture", "media_type": mimetype})
                self.assertEqual(response.status_code, 200)
                media.assert_awaited_once()
                text.assert_not_awaited()

    def test_invalid_base64_and_media_type_mismatch_are_rejected(self):
        self.assertEqual(self.send({"base64": "@@@", "media_type": "image/png"}).status_code, 422)
        self.assertEqual(self.send({
            "base64": base64.b64encode(valid_png()).decode(), "media_type": "video",
        }).status_code, 415)

    def test_simulator_is_not_saved_as_a_real_conversation(self):
        with patch("app.api.whatsapp.run_pipeline", new=AsyncMock(return_value={"report": {}})), patch(
            "app.api.whatsapp.save_anonymous_history", new=AsyncMock()
        ) as history:
            self.assertEqual(self.client.post("/api/whatsapp/simulate", json={"message": "Texto de controle", "from_number": "fixture"}).status_code, 200)
        history.assert_not_awaited()
        self.assertEqual(self.client.post("/api/whatsapp/simulate", json={"message": ""}).status_code, 422)

    def test_sender_hash_uses_an_independent_secret_and_fails_closed(self):
        with patch.dict(os.environ, {"WHATSAPP_HASH_SECRET": "h" * 40}):
            hashed = _hash_sender("fixture-number")
        self.assertNotEqual(hashed, hashlib.sha256(b"fixture-number").hexdigest())
        with patch.dict(os.environ, {"WHATSAPP_HASH_SECRET": ""}), self.assertRaises(ValueError):
            _hash_sender("fixture-number")

    def test_receipt_capacity_is_bounded_without_evicting_active_ids(self):
        guard = ReceiptGuard(capacity=1)
        self.assertTrue(guard.claim("first"))
        self.assertFalse(guard.claim("first"))
        with self.assertRaises(HTTPException):
            guard.claim("second")
        guard.release("first")
        self.assertTrue(guard.claim("second"))


class RequestBudgetTests(unittest.TestCase):
    def client(self, **limits):
        fixture = FastAPI()
        @fixture.post("/api/check-text")
        @fixture.post("/api/auth/register")
        async def analyze(request: Request):
            return {"size": len(await request.body())}
        @fixture.get("/health")
        async def health():
            return {"status": "ok"}
        fixture.add_middleware(RequestBudgetMiddleware, **limits)
        return TestClient(fixture)

    def test_analysis_and_registration_limits_ignore_spoofed_forward_headers(self):
        for path in ("/api/check-text", "/api/auth/register"):
            with self.subTest(path=path):
                client = self.client(per_ip=2, global_limit=20)
                self.assertEqual(client.post(path, content="small").status_code, 200)
                self.assertEqual(client.post(path, headers={"X-Forwarded-For": "different"}, content="small").status_code, 200)
                response = client.post(path, content="small")
                self.assertEqual(response.status_code, 429)
                self.assertIn("Retry-After", response.headers)
                self.assertEqual(client.get("/health").status_code, 200)

    def test_global_limit_remains_stable_on_repeated_rejection(self):
        client = self.client(per_ip=10, global_limit=1)
        self.assertEqual(client.post("/api/check-text").status_code, 200)
        for _ in range(3):
            self.assertEqual(client.post("/api/check-text").status_code, 429)

    def test_large_known_length_and_chunked_bodies_are_rejected(self):
        client = self.client(per_ip=10, global_limit=20, max_body=8)
        self.assertEqual(client.post("/api/check-text", content=b"x" * 9).status_code, 413)
        response = client.post("/api/check-text", content=iter([b"12345", b"67890"]))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(client.post("/api/check-text", content="small").status_code, 200)

    def test_cross_site_writes_rejected_even_when_simple_form_has_no_preflight(self):
        client = self.client()
        for origin in ("https://attacker.vercel.app", "null"):
            self.assertEqual(client.post("/api/check-text", content="small", headers={"Origin": origin}).status_code, 403)
        self.assertEqual(client.post("/api/check-text", content="small", headers={"Origin": "http://localhost:5173"}).status_code, 200)

    def test_cors_wildcard_does_not_allow_unrelated_vercel_projects(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "*", "CORS_ORIGIN_REGEX": ""}):
            client = self.client()
            self.assertEqual(client.post("/api/check-text", headers={"Origin": "https://attacker.vercel.app"}).status_code, 403)

    def test_slow_body_releases_capacity_after_timeout(self):
        called = AsyncMock()
        middleware = RequestBudgetMiddleware(called, per_ip=10, global_limit=20, body_timeout=.01)
        scope = {"type": "http", "method": "POST", "path": "/api/check-text", "headers": [], "client": ("fixture", 1)}
        async def receive():
            await asyncio.sleep(.05)
        send = AsyncMock()
        asyncio.run(middleware(scope, receive, send))
        self.assertEqual(send.call_args_list[0].args[0]["status"], 408)
        self.assertEqual(middleware.active, 0)
        self.assertFalse(middleware.active_by_ip)
        called.assert_not_awaited()

    def test_concurrency_is_bounded_and_released(self):
        async def scenario():
            entered, release = asyncio.Event(), asyncio.Event()
            async def handler(scope, receive, send):
                entered.set()
                await release.wait()
            middleware = RequestBudgetMiddleware(handler, per_ip=10, global_limit=20, concurrency=1)
            scope = {"type": "http", "method": "POST", "path": "/api/check-text", "headers": [], "client": ("fixture", 1)}
            receive = AsyncMock(return_value={"type": "http.request", "body": b""})
            first = asyncio.create_task(middleware(scope, receive, AsyncMock()))
            await entered.wait()
            send = AsyncMock()
            await middleware(scope, receive, send)
            self.assertEqual(send.call_args_list[0].args[0]["status"], 429)
            release.set()
            await first
            self.assertEqual(middleware.active, 0)
        asyncio.run(scenario())
