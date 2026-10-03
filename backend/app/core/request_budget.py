"""Single-worker admission limits. Use shared limits/WAF before scaling out."""

import asyncio
import os
import re
import time
from collections import OrderedDict, deque

from starlette.responses import JSONResponse
from starlette.requests import Request
from fastapi import HTTPException
from app.services.whatsapp_security import authenticate_webhook

ANALYSIS_PATHS = (
    "/api/check-text", "/api/check-url", "/api/upload", "/api/whatsapp/",
    "/api/verificar/", "/api/capturar/", "/api/selo/", "/api/analyze-batch",
)
AUTH_PATHS = {"/api/auth/login", "/api/auth/register", "/api/auth/google"}


def _positive_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


class RequestBudgetMiddleware:
    def __init__(
        self, app, *, per_ip: int | None = None, global_limit: int | None = None,
        concurrency: int | None = None, max_body: int | None = None,
        window: float = 60.0, body_timeout: float = 15.0,
    ):
        self.app = app
        self.per_ip = per_ip or _positive_env("ANALYSIS_REQUESTS_PER_MINUTE", 10)
        self.global_limit = global_limit or _positive_env("ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE", 60)
        self.concurrency = concurrency or _positive_env("ANALYSIS_MAX_CONCURRENT", 4)
        self.max_body = max_body or _positive_env("API_MAX_BODY_BYTES", 35 * 1024 * 1024)
        self.window = window
        self.body_timeout = body_timeout
        self.clients: OrderedDict[tuple[str, str], deque] = OrderedDict()
        self.global_requests: deque = deque()
        self.active = 0
        self.active_by_ip: dict[str, int] = {}
        self.origins = {
            origin.strip() for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
            ).split(",") if origin.strip() and origin.strip() != "*"
        }
        regex = os.getenv("CORS_ORIGIN_REGEX", "")
        self.origin_regex = re.compile(regex) if regex else None

    async def _reject(self, scope, receive, send, code: int, detail: str, retry: bool = False):
        headers = {"Retry-After": str(max(1, int(self.window)))} if retry else {}
        await JSONResponse({"detail": detail}, code, headers=headers)(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method, path = scope["method"], scope["path"]
        headers = dict(scope.get("headers", []))
        # CORS alone does not stop side effects from a simple cross-site form.
        origin = headers.get(b"origin", b"").decode("latin-1")
        if method not in {"GET", "HEAD", "OPTIONS"} and origin:
            if origin not in self.origins and not (self.origin_regex and self.origin_regex.fullmatch(origin)):
                return await self._reject(scope, receive, send, 403, "Origem não autorizada.")
        is_auth = path in AUTH_PATHS
        is_analysis = path.startswith(ANALYSIS_PATHS)
        if method != "POST" or not (is_auth or is_analysis):
            return await self.app(scope, receive, send)
        if path == "/api/whatsapp/webhook":
            try:
                authenticate_webhook(Request(scope))
            except HTTPException as exc:
                return await self._reject(scope, receive, send, exc.status_code, exc.detail)
        # Only the ASGI server may resolve trusted proxies. Never trust client headers here.
        ip = (scope.get("client") or ("unknown", 0))[0]
        now = time.monotonic()
        cutoff = now - self.window
        while self.clients and next(iter(self.clients.values()))[-1] <= cutoff:
            self.clients.popitem(last=False)
        bucket_key = (ip, "auth" if is_auth else "analysis")
        bucket = self.clients.get(bucket_key)
        if bucket is None:
            if len(self.clients) >= 10000:
                return await self._reject(scope, receive, send, 429, "Limite de solicitações atingido.", True)
            bucket = deque()
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        while self.global_requests and self.global_requests[0] <= cutoff:
            self.global_requests.popleft()
        ip_limit = min(self.per_ip, 10) if is_auth else self.per_ip
        if len(bucket) >= ip_limit or len(self.global_requests) >= self.global_limit:
            return await self._reject(scope, receive, send, 429, "Limite de solicitações atingido. Aguarde antes de tentar novamente.", True)
        bucket.append(now)
        self.clients[bucket_key] = bucket
        self.clients.move_to_end(bucket_key)
        self.global_requests.append(now)
        if self.active >= self.concurrency or self.active_by_ip.get(ip, 0) >= 2:
            return await self._reject(scope, receive, send, 429, "Muitas análises em andamento. Tente novamente mais tarde.", True)
        limit = min(self.max_body, 64 * 1024) if is_auth else self.max_body
        declared = headers.get(b"content-length", b"")
        if declared.isdigit() and int(declared) > limit:
            return await self._reject(scope, receive, send, 413, "Envio excede o limite de tamanho da requisição.")
        self.active += 1
        self.active_by_ip[ip] = self.active_by_ip.get(ip, 0) + 1
        try:
            # Bounded buffering catches chunked uploads before multipart/JSON parsing.
            body = bytearray()
            try:
                async with asyncio.timeout(self.body_timeout):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > limit:
                            return await self._reject(scope, receive, send, 413, "Envio excede o limite de tamanho da requisição.")
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await self._reject(scope, receive, send, 408, "O envio excedeu o tempo permitido.")
            consumed = False

            async def bounded_receive():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, send)
        finally:
            self.active -= 1
            self.active_by_ip[ip] -= 1
            if not self.active_by_ip[ip]:
                del self.active_by_ip[ip]
