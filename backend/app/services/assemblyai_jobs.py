"""Private, bounded AssemblyAI resume guard for ONE process and a finite window.

This caches transcription operations, never media/factual verdicts. Pending and
uncertain submissions survive requester cancellation for 30 minutes, followed
by a five-minute expired tombstone. After removal/restart/another worker there
is no deduplication guarantee. No provider ID or upload URL is a public token.
"""

import asyncio
import copy
from dataclasses import dataclass
import hashlib
import hmac
import json
import math
import re
import secrets
import time
from urllib.parse import urlsplit

import httpx

ASSEMBLYAI_API_URL = "https://api.assemblyai.com/v2"
MODEL = "universal-2"
LANGUAGE = "pt"
OPTIONS_VERSION = "resume-v1"
PUBLIC_FIELDS = frozenset({"available", "status", "transcription", "reason",
                           "model_used", "decision_role", "confidence",
                           "words_count", "audio_duration_sec"})


def _unavailable(status: str, reason: str) -> dict:
    return {"available": False, "status": status, "transcription": "", "reason": reason}


def _upload_url(value) -> str:
    # Official upload API examples use this exact hostname. The server does not
    # fetch it: it is passed only back to the fixed AssemblyAI submit endpoint.
    # https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/files/upload
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) <= 32 for c in value):
        raise ValueError("Invalid upload URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname != "cdn.assemblyai.com"
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in {None, 443} or parsed.fragment or not parsed.path):
        raise ValueError("Invalid upload URL")
    return value


def _data(response: httpx.Response) -> dict:
    if len(response.content) > 2 * 1024 * 1024:
        raise ValueError("Invalid provider response")
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid provider response")
    return payload


def _number(value, maximum: float):
    return value if (type(value) in {int, float} and math.isfinite(value)
                     and 0 <= value <= maximum) else None


def _completed(payload: dict) -> dict:
    text = payload.get("text")
    if not isinstance(text, str) or len(text) > 100000:
        raise ValueError("Invalid transcript")
    if not text.strip():
        return _unavailable("no_speech", "O provedor não encontrou fala transcritível.")
    model = payload.get("speech_model_used") or MODEL
    if not isinstance(model, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", model):
        model = MODEL
    words = payload.get("words")
    return {"available": True, "status": "success", "transcription": text.strip(),
            "model_used": model, "decision_role": "transcription_only",
            "confidence": _number(payload.get("confidence"), 1),
            "words_count": len(words) if isinstance(words, list) and len(words) <= 10000 else None,
            "audio_duration_sec": _number(payload.get("audio_duration"), 180)}


@dataclass
class _Record:
    retained_until: float
    phase: str = "new"
    job_id: str | None = None
    result: dict | None = None
    result_until: float | None = None
    task: asyncio.Task | None = None
    expiry_timer: asyncio.TimerHandle | None = None
    removal_timer: asyncio.TimerHandle | None = None


class AssemblyAIJobs:
    """Atomic scoped operations. No byte, URL or credential stored in records."""

    def __init__(self, *, capacity=64, active_limit=8, pending_ttl=1800,
                 success_ttl=300, error_ttl=60, tombstone_ttl=300,
                 worker_timeout=25, waiter_timeout=25, max_polls=16,
                 clock=time.monotonic, transport=None):
        self.capacity, self.active_limit = capacity, active_limit
        self.pending_ttl, self.success_ttl = pending_ttl, success_ttl
        self.error_ttl, self.tombstone_ttl = error_ttl, tombstone_ttl
        self.worker_timeout, self.waiter_timeout = worker_timeout, waiter_timeout
        self.max_polls, self.clock = max_polls, clock
        self.transport = transport
        self._records: dict[str, _Record] = {}
        self._lock = asyncio.Lock()
        self._salt = secrets.token_bytes(32)

    def _key(self, data: bytes, api_key: str, namespace: str | None) -> str:
        # Absent/invalid context must not become a shared anonymous namespace.
        if not isinstance(namespace, str) or not namespace or len(namespace) > 512:
            namespace = "ephemeral:" + secrets.token_urlsafe(32)
        components = [namespace, hashlib.sha256(data).hexdigest(),
                      hashlib.sha256(api_key.encode()).hexdigest(), MODEL, LANGUAGE, OPTIONS_VERSION]
        return hmac.new(self._salt, json.dumps(components).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _active(record: _Record) -> bool:
        return record.task is not None and not record.task.done()

    @staticmethod
    def _clear(record: _Record):
        for timer in (record.expiry_timer, record.removal_timer):
            if timer is not None:
                timer.cancel()
        record.expiry_timer, record.removal_timer = None, None
        record.result, record.job_id, record.task = None, None, None

    def _discard(self, key: str, record: _Record):
        if self._records.get(key) is record:
            self._clear(record)
            del self._records[key]

    def _remove_expired(self, key: str, record: _Record):
        if self._records.get(key) is not record:
            return
        if self._active(record):
            # Do not evict a live operation and allow another upload to race it.
            record.task.add_done_callback(lambda _task: self._discard(key, record))
        else:
            self._discard(key, record)

    def _expire(self, key: str, record: _Record):
        if self._records.get(key) is not record:
            return
        now = self.clock()
        if record.result_until is not None:
            if now < record.result_until:
                return
            # Remove transcript on its fixed deadline, even while idle.
            record.result, record.job_id, record.phase = None, None, "blocked_expired"
            self._remove_expired(key, record)
            return
        if now < record.retained_until:
            return
        record.result, record.job_id, record.phase = None, None, "blocked_expired"
        if record.expiry_timer is not None:
            record.expiry_timer.cancel()
            record.expiry_timer = None
        if now >= record.retained_until + self.tombstone_ttl:
            self._remove_expired(key, record)
        elif record.removal_timer is None:
            record.removal_timer = asyncio.get_running_loop().call_later(
                record.retained_until + self.tombstone_ttl - now,
                self._remove_expired, key, record,
            )

    def _schedule_expiry(self, key: str, record: _Record, deadline: float):
        if record.expiry_timer is not None:
            record.expiry_timer.cancel()
        record.expiry_timer = asyncio.get_running_loop().call_later(
            max(0, deadline - self.clock()), self._expire, key, record,
        )

    def _prune(self):
        now = self.clock()
        for key, record in list(self._records.items()):
            if record.result_until is not None:
                if now >= record.result_until:
                    self._expire(key, record)
                continue
            if now >= record.retained_until:
                # Expired jobs cannot be resumed or silently recreated during
                # the fixed tombstone interval. Readers do not extend any TTL.
                self._expire(key, record)

    def _public(self, record: _Record) -> dict:
        if record.phase == "blocked_expired":
            return _unavailable("blocked_expired", "A janela privada de retomada expirou. Não foi criada outra tarefa automaticamente nesta janela.")
        if self.clock() >= record.retained_until and record.result_until is None:
            return _unavailable("blocked_expired", "A janela privada de retomada expirou. Não foi criada outra tarefa automaticamente nesta janela.")
        if record.result is not None:
            return copy.deepcopy({key: value for key, value in record.result.items() if key in PUBLIC_FIELDS})
        if record.phase == "blocked_uncertain":
            return _unavailable("blocked_uncertain", "Não foi possível confirmar a criação da transcrição. Novo envio ao provedor está bloqueado temporariamente para evitar duplicação.")
        if self._active(record):
            return _unavailable("in_progress", "Uma transcrição deste arquivo já está em andamento nesta sessão. Nenhuma nova tarefa foi criada.")
        return _unavailable("pending", "A transcrição está pendente. Uma nova tentativa nesta sessão consultará a tarefa existente, dentro da janela privada de retomada.")

    def _terminal(self, key: str, record: _Record, result: dict):
        record.phase, record.result = "done", result
        ttl = self.success_ttl if result.get("status") in {"success", "no_speech"} else self.error_ttl
        # Completion cannot extend an already expired pending window.
        if self.clock() >= record.retained_until:
            record.phase, record.result, record.job_id = "blocked_expired", None, None
            return
        record.result_until = self.clock() + ttl
        self._schedule_expiry(key, record, record.result_until)

    async def _round(self, key: str, record: _Record, file_bytes: bytes | None, api_key: str):
        try:
            async with asyncio.timeout(self.worker_timeout):
                async with httpx.AsyncClient(timeout=10.0, trust_env=False, follow_redirects=False, transport=self.transport) as client:
                    headers = {"authorization": api_key}
                    if record.job_id is None:
                        record.phase = "uploading"
                        upload = await client.post(f"{ASSEMBLYAI_API_URL}/upload",
                                                   headers={**headers, "content-type": "application/octet-stream"}, content=file_bytes)
                        file_bytes = None  # Never retain audio during polling.
                        if upload.status_code != 200:
                            self._terminal(key, record, _unavailable("error", f"Upload AssemblyAI indisponível (HTTP {upload.status_code})."))
                            return
                        audio_url = _upload_url(_data(upload).get("upload_url"))
                        upload = None
                        record.phase = "submitting"
                        submit = await client.post(f"{ASSEMBLYAI_API_URL}/transcript", headers=headers,
                                                   json={"audio_url": audio_url, "language_code": LANGUAGE, "speech_models": [MODEL]})
                        audio_url = None
                        if 400 <= submit.status_code < 500:
                            self._terminal(key, record, _unavailable("error", f"Criação da transcrição recusada (HTTP {submit.status_code})."))
                            return
                        # 5xx/redirect/invalid JSON/no ID can be ambiguous after
                        # POST. Never automatically submit another billed job.
                        if submit.status_code not in {200, 201}:
                            record.phase = "blocked_uncertain"
                            return
                        job_id = _data(submit).get("id")
                        if not isinstance(job_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", job_id):
                            record.phase = "blocked_uncertain"
                            return
                        record.job_id = job_id  # Private checkpoint BEFORE polling.
                        submit = None
                    record.phase = "polling"
                    for attempt in range(self.max_polls):
                        if self.clock() >= record.retained_until:
                            record.phase, record.job_id = "blocked_expired", None
                            return
                        poll = await client.get(f"{ASSEMBLYAI_API_URL}/transcript/{record.job_id}", headers=headers)
                        if poll.status_code != 200:
                            record.phase = "pending"
                            return
                        payload = _data(poll)
                        status = payload.get("status")
                        if status == "completed":
                            self._terminal(key, record, _completed(payload))
                            payload = None
                            return
                        if status == "error":
                            self._terminal(key, record, _unavailable("error", "Transcrição recusada pelo provedor."))
                            return
                        if status not in {"queued", "processing"}:
                            record.phase = "pending"
                            return
                        if attempt + 1 < self.max_polls:
                            await asyncio.sleep(min(.5 * (attempt + 1), 2))
                    record.phase = "pending"
        except asyncio.CancelledError:
            self._interrupted(key, record)
            raise
        except Exception:
            self._interrupted(key, record)
        finally:
            # Even an externally cancelled Task must not keep response/request
            # objects (raw audio/auth headers) through a retained traceback.
            file_bytes, api_key, headers = None, "", None
            upload, submit, poll, payload, audio_url = None, None, None, None, None
            if self.clock() >= record.retained_until and record.result_until is None:
                record.phase, record.result, record.job_id = "blocked_expired", None, None

    def _interrupted(self, key: str, record: _Record):
        if record.job_id is not None:
            record.phase = "pending"
        elif record.phase == "submitting":
            record.phase = "blocked_uncertain"
        else:
            self._terminal(key, record, _unavailable("error", "Resposta de transcrição indisponível ou inválida."))

    async def transcribe(self, file_bytes: bytes, api_key: str, namespace: str | None = None) -> dict:
        if not isinstance(file_bytes, bytes) or not file_bytes or len(file_bytes) > 25 * 1024 * 1024:
            return _unavailable("invalid_input", "Áudio ausente ou fora dos limites de envio.")
        key = self._key(file_bytes, api_key, namespace)
        async with self._lock:
            self._prune()
            record = self._records.get(key)
            if record is not None and (record.result is not None or record.phase in {"blocked_uncertain", "blocked_expired"}):
                return self._public(record)
            if record is None or not self._active(record):
                if (record is None and len(self._records) >= self.capacity
                        or sum(self._active(item) for item in self._records.values()) >= self.active_limit):
                    return _unavailable("capacity_exceeded", "Limite privado de transcrições em andamento ou retidas atingido. Nenhuma tarefa nova foi criada.")
                if record is None:
                    record = _Record(self.clock() + self.pending_ttl)
                    self._records[key] = record
                    self._schedule_expiry(key, record, record.retained_until)
                record.task = asyncio.create_task(self._round(key, record, file_bytes if record.job_id is None else None, api_key))
            task = record.task
        # A requester timeout/disconnect must not cancel the single shared
        # upload/submit operation. Worker still has its own total deadline.
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=self.waiter_timeout)
        except asyncio.TimeoutError:
            pass
        async with self._lock:
            self._prune()
            return self._public(record)

    async def shutdown(self):
        tasks = [record.task for record in self._records.values() if self._active(record)]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for record in self._records.values():
            self._clear(record)
        self._records.clear()


assemblyai_jobs = AssemblyAIJobs()
