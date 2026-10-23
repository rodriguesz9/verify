"""Bounded Gemini REST calls, honoring explicit model configuration."""
import asyncio
import base64
from collections import deque
import json
import math
import os
import re
import threading
import time
import httpx


MAX_GEMINI_REQUEST_BYTES = 19_000_000  # Below Google's 20 MB inline request cap.


class GeneratedText(str):
    model_name: str


class GeminiError(RuntimeError):
    def __init__(self, reason, status="error", http_status=None):
        self.status, self.http_status = status, http_status
        super().__init__(reason)


def _bounded_integer(name, default, lower, upper):
    raw = os.getenv(name, str(default)).strip()
    if not re.fullmatch(r"[0-9]{1,4}", raw):
        return default
    value = int(raw)
    return value if lower <= value <= upper else default


def _admission_enabled():
    # Explicit opt-out used by isolated regression harnesses. Other values do
    # not silently remove protection from a misconfigured production service.
    return os.getenv("GEMINI_LOCAL_ADMISSION_ENABLED", "true").strip().lower() != "false"


class GeminiAdmission:
    """Bounded per-process burst protection, NOT the Google project's quota.

    All callers using this REST helper share a model window, including failed
    requests and explicit fallbacks. No key, input, media or response is stored.
    Other processes, API clients and services using the project are not covered.
    """

    def __init__(self, *, clock=time.monotonic, capacity=32):
        self._clock = clock
        self._capacity = capacity
        self._lock = threading.Lock()
        self._models = {}
        self._waiters = {}
        self._pending_count = 0

    def _prune(self, now):
        for model, record in list(self._models.items()):
            stamps, paused_until = record
            while stamps and now - stamps[0] >= 60:
                stamps.popleft()
            if not stamps and now >= paused_until and not self._waiters.get(model):
                del self._models[model]

    def _record(self, model, now):
        # Called only with the process lock held. Pending models keep their
        # record during pruning so another model cannot steal its state slot.
        self._prune(now)
        record = self._models.get(model)
        if record is None:
            if len(self._models) >= self._capacity:
                raise GeminiError("Serviço de leitura temporariamente ocupado. Aguarde antes de tentar novamente.", "rate_limited")
            record = self._models[model] = [deque(), 0.0]
        if now < record[1]:
            raise GeminiError("Serviço de leitura em pausa após limite de solicitações. Aguarde antes de tentar novamente.", "rate_limited")
        return record

    def _wake_waiters(self, model):
        # The lock owns state across threads/loops; each event is touched only
        # by its own loop. Tickets hold no payload, key, media or response.
        for loop, event in self._waiters.get(model, ()):
            try:
                loop.call_soon_threadsafe(event.set)
            except RuntimeError:
                pass  # Loop shutdown cancels pending tasks and runs cleanup.

    def reserve(self, model, requests_per_minute):
        """Immediate reservation for synchronous callers; never jump a queue."""
        with self._lock:
            now = self._clock()
            record = self._record(model, now)
            if self._waiters.get(model) or len(record[0]) >= requests_per_minute:
                raise GeminiError("Muitas solicitações de leitura em pouco tempo. Aguarde antes de tentar novamente.", "rate_limited")
            # Failed/ambiguous requests also consume the local burst budget.
            record[0].append(now)

    async def wait(self, model, requests_per_minute):
        """Wait only for the local window, within the caller's same deadline.

        At most 32 pending tickets in this process, FIFO per model. No task or
        HTTP request is detached. Cancellation while queued removes the ticket
        without consuming a slot; after reservation an attempted/ambiguous
        transport remains charged. Provider cooldown never waits or retries.
        """
        ticket = (asyncio.get_running_loop(), asyncio.Event())
        with self._lock:
            now = self._clock()
            record = self._record(model, now)
            if not self._waiters.get(model) and len(record[0]) < requests_per_minute:
                record[0].append(now)
                return
            if self._pending_count >= 32:
                raise GeminiError("Fila de leitura temporariamente cheia. Aguarde antes de tentar novamente.", "rate_limited")
            self._waiters.setdefault(model, deque()).append(ticket)
            self._pending_count += 1
        queued = True
        try:
            while True:
                with self._lock:
                    now = self._clock()
                    record = self._record(model, now)
                    queue = self._waiters[model]
                    if queue[0] is ticket and len(record[0]) < requests_per_minute:
                        queue.popleft()
                        self._pending_count -= 1
                        queued = False
                        if not queue:
                            del self._waiters[model]
                        record[0].append(now)
                        self._wake_waiters(model)
                        return
                    ticket[1].clear()
                    delay = (max(0.0, record[0][0] + 60 - now)
                             if queue[0] is ticket and len(record[0]) >= requests_per_minute else None)
                if delay is None:
                    await ticket[1].wait()
                else:
                    try:
                        # A local timer rechecks the same window; it does not
                        # extend generate_text's or the caller's deadline.
                        async with asyncio.timeout(delay):
                            await ticket[1].wait()
                    except TimeoutError:
                        pass
        finally:
            if queued:
                with self._lock:
                    queue = self._waiters.get(model)
                    if queue is not None and ticket in queue:
                        queue.remove(ticket)
                        self._pending_count -= 1
                        if not queue:
                            del self._waiters[model]
                        self._wake_waiters(model)

    def pause(self, model, duration):
        with self._lock:
            now = self._clock()
            self._prune(now)
            record = self._models.get(model)
            if record is None:
                if len(self._models) >= self._capacity:
                    return
                record = self._models[model] = [deque(), 0.0]
            record[1] = max(record[1], now + duration)
            self._wake_waiters(model)


_gemini_admission = GeminiAdmission()


async def _reserve_request(model):
    if _admission_enabled():
        await _gemini_admission.wait(model, _bounded_integer("GEMINI_LOCAL_REQUESTS_PER_MINUTE", 5, 1, 15))


def _pause_after_rate_limit(model, response):
    if not _admission_enabled():
        return
    duration = _bounded_integer("GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", 60, 1, 3600)
    retry_after = response.headers.get("retry-after", "").strip()
    if re.fullmatch(r"[0-9]{1,9}", retry_after):
        duration = max(duration, min(3600, max(1, int(retry_after))))
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        details = error.get("details", []) if isinstance(error, dict) else []
        if isinstance(details, list):
            for detail in details[:16]:
                if not isinstance(detail, dict) or detail.get("@type") != "type.googleapis.com/google.rpc.RetryInfo":
                    continue
                delay = detail.get("retryDelay")
                if isinstance(delay, str) and re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,9})?s", delay):
                    duration = max(duration, min(3600, max(1, float(delay[:-1]))))
    except (ValueError, TypeError, AttributeError):
        pass  # Error bodies, messages and configuration values never escape.
    _gemini_admission.pause(model, duration)


def _validate_request_size(body):
    try:
        size = len(json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    except (ValueError, TypeError, OverflowError):
        raise GeminiError("Configuração da solicitação de leitura inválida.", "invalid_configuration") from None
    if size > MAX_GEMINI_REQUEST_BYTES:
        raise GeminiError("Arquivo grande demais para leitura remota. Use uma imagem menor ou um trecho mais curto do áudio.", "input_too_large")


def gemini_timeout_seconds() -> int:
    """One bounded deadline; malformed private configuration is never echoed."""
    raw = os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "60").strip()
    if not re.fullmatch(r"[0-9]{1,2}", raw):
        return 60
    value = int(raw)
    return value if 10 <= value <= 90 else 60


async def generate_text(contents, *, system_instruction=None, temperature=.1, json_output=True, max_tokens=2048, model_name=None, response_schema=None, timeout_seconds=None):
    deadline = gemini_timeout_seconds() if timeout_seconds is None else timeout_seconds
    if (isinstance(deadline, bool) or not isinstance(deadline, (int, float))
            or not math.isfinite(deadline) or not 0 < deadline <= 90):
        raise GeminiError("Prazo da solicitação de leitura inválido.", "invalid_configuration")
    try:
        # The explicit fallback shares the deadline, not a second full budget.
        async with asyncio.timeout(deadline):
            return await _generate_text(contents, system_instruction=system_instruction,
                temperature=temperature, json_output=json_output, max_tokens=max_tokens,
                model_name=model_name, response_schema=response_schema, deadline=deadline)
    except TimeoutError:
        raise GeminiError("Tempo limite do Gemini atingido.", "timeout") from None


async def _generate_text(contents, *, system_instruction=None, temperature=.1, json_output=True, max_tokens=2048, model_name=None, response_schema=None, deadline=60):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("Gemini não configurado.", "not_configured")
    primary = model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash").strip()
    fallback = [] if model_name else [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
    models = list(dict.fromkeys([primary, *fallback]))[:2]
    if any(not re.fullmatch(r"[a-zA-Z0-9._-]{1,120}", model) for model in models):
        raise GeminiError("Identificador de modelo Gemini inválido.", "invalid_configuration")
    parts = []
    for part in contents if isinstance(contents, list) else [contents]:
        if isinstance(part, str):
            parts.append({"text": part})
        elif "inline_data" in part:
            inline = part["inline_data"]
            parts.append({"inlineData": {"mimeType": inline["mime_type"], "data": base64.b64encode(inline["data"]).decode()}})
        else:
            parts.append(part)
    config = {"temperature": temperature, "maxOutputTokens": max(64, min(4096, max_tokens))}
    if json_output:
        config["responseMimeType"] = "application/json"
        if response_schema:
            config["responseSchema"] = response_schema
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": config}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    transport_timeout = httpx.Timeout(deadline, connect=min(10, deadline), write=min(15, deadline), pool=5)
    async with httpx.AsyncClient(timeout=transport_timeout, trust_env=False, follow_redirects=False) as client:
        for index, model in enumerate(models):
            # Simple extraction/OCR needs low latency, not default deep reasoning.
            # thinkingLevel is documented only for Gemini 3+; no legacy breakage.
            body["generationConfig"] = {**config, **({"thinkingConfig": {"thinkingLevel": "LOW"}} if model.startswith("gemini-3") else {})}
            _validate_request_size(body)
            await _reserve_request(model)
            try:
                response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                             headers={"x-goog-api-key": key}, json=body)
            except httpx.TimeoutException:
                if index + 1 < len(models):
                    continue
                raise GeminiError("Tempo limite do Gemini atingido.", "timeout") from None
            except httpx.HTTPError:
                raise GeminiError("Conexão Gemini indisponível.") from None
            if response.status_code in {404, 503} and index + 1 < len(models):
                continue
            if response.status_code != 200:
                if response.status_code == 429:
                    _pause_after_rate_limit(model, response)
                status = "rate_limited" if response.status_code == 429 else "unavailable" if response.status_code == 503 else "error"
                raise GeminiError(f"Gemini indisponível (HTTP {response.status_code}).", status, response.status_code)
            try:
                candidates = response.json().get("candidates", [])
                if not candidates or candidates[0].get("finishReason") not in {None, "STOP"}:
                    raise ValueError("incomplete")
                value = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []) if not p.get("thought"))
                if not value or len(value) > 30000:
                    raise ValueError("empty or oversized")
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                raise GeminiError("Gemini não retornou uma resposta completa e válida.", "invalid_response") from None
            text = GeneratedText(value)
            text.model_name = model
            return text
