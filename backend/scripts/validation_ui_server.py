"""Disposable UI validation server; not a deploy configuration.

Only explicitly selected providers receive public test content. Hive additionally
requires an existing-credit paid-budget opt-in for two images and five cumulative
rounded audio seconds, with no paid retry. Private .env uses an allowlist: no
production DB/auth configuration is imported. Reservations persist before sends.
Use --container only with Docker bound to 127.0.0.1 on the host.
"""
import argparse
import asyncio
from collections import Counter
from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import ipaddress
import math
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading

KEYS = {
    "gemini": ("GEMINI_API_KEY",), "openrouter": ("OPENROUTER_API_KEY",),
    "facts": ("GOOGLE_FACT_CHECK_KEY",), "news": ("SERPERAPI_KEY",),
    "assemblyai": ("ASSEMBLYAI_API_KEY",),
    "sightengine": ("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
    "hf": ("HUGGINGFACE_API_TOKEN",),
    "hive": ("HIVE_V3_API_KEY", "HIVE_API_KEY"),
    "public_fetch": (),
}
CAPS = {"gemini": 12, "openrouter": 9, "facts": 40, "news": 22,
        "assemblyai": 40, "sightengine": 3, "hf": 2, "public_fetch": 4, "hive": 3}
MAX_CAPS = {**CAPS, "sightengine": 6, "public_fetch": 40}
HIVE_QA_CAPS = {"image_requests": 2, "audio_seconds": 5, "audio_jobs": 1}
HOSTS = {"generativelanguage.googleapis.com": "gemini", "openrouter.ai": "openrouter",
         "factchecktools.googleapis.com": "facts", "google.serper.dev": "news",
         "api.assemblyai.com": "assemblyai", "api.sightengine.com": "sightengine",
         "router.huggingface.co": "hf", "api.thehive.ai": "hive",
         "www.nasa.gov": "public_fetch", "science.nasa.gov": "public_fetch"}
LOCAL_PAGE_CONTROL_URL = "https://example.test/controle.html"
DIAGNOSTIC_TEXT_CONTROLS = {
    "queen_true": "Elizabeth II morreu em 8 de setembro de 2022.",
    "queen_false": "Elizabeth II morreu em 9 de setembro de 2022.",
    "apollo_true": "A missão Apollo 11 foi lançada em 16 de julho de 1969.",
    "moon_false": "O homem nunca pisou na Lua.",
}
DIAGNOSTIC_FIXED_SOURCES = {"royal": "https://www.royal.uk/the-king",
                            "uol": "https://brasilescola.uol.com.br/historia/elizabeth-ii.htm"}


def local_page_control_fetch(original):
    """Explicit QA-only HTTP simulation. All other URLs keep the SSRF defense."""
    async def fetch(url, **kwargs):
        if url != LOCAL_PAGE_CONTROL_URL:
            return await original(url, **kwargs)
        from fastapi import HTTPException
        from app.services.public_fetch import FetchedResource
        fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/validation/links/pagina-controle.html"
        data = fixture.read_bytes()
        if len(data) > kwargs["max_bytes"]:
            raise HTTPException(413, "Controle local excede limite.")
        if kwargs.get("allowed_types") and "text/html" not in kwargs["allowed_types"]:
            raise HTTPException(415, "Controle local é HTML.")
        return FetchedResource(data, "text/html", LOCAL_PAGE_CONTROL_URL, "utf-8")
    return fetch


def request_provider(request):
    provider = HOSTS.get(request.url.host)
    if provider == "hive":
        from app.services.hive_service import HIVE_V3_API_URL
        return "hive" if request.method == "POST" and str(request.url) == HIVE_V3_API_URL else None
    if provider:
        return provider
    # The application's SSRF defense connects to a validated, pinned IP.
    # Recognize only our public fixture hosts; do not remove IP pinning or TLS.
    sni = request.extensions.get("sni_hostname")
    if isinstance(sni, bytes):
        sni = sni.decode("ascii", errors="ignore")
    allowed_source = sni in {"www.nasa.gov", "science.nasa.gov"}
    if not allowed_source or request.headers.get("host") != sni:
        return None
    try:
        if request.url.scheme == "https" and request.url.port in {None, 443} and ipaddress.ip_address(request.url.host).is_global:
            return "public_fetch"
    except ValueError:
        pass
    return None


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--providers", default="")
    parser.add_argument("--free-credits-confirmed", action="store_true")
    parser.add_argument("--hive-paid-budget-approved", action="store_true",
                        help="Explicit existing-credit approval: at most two Hive image calls, one audio call and five rounded audio seconds; no refill/retry.")
    parser.add_argument("--gemini-model", default="gemini-3.7-flash")
    parser.add_argument("--media-model", default="gemini-3.1-flash-lite")
    parser.add_argument("--gemini-request-cap", type=int, choices=range(13), default=12,
                        help="Optional stricter ceiling when separate diagnostics already consumed budget.")
    parser.add_argument("--public-fetch-cap", type=int, choices=range(41), default=None,
                        help="Explicit session ceiling for safe public-source HTTP reads, including redirects; maximum 40.")
    parser.add_argument("--sightengine-request-cap", type=int, choices=range(7), default=3,
                        help="Explicit free-credit session ceiling, at most six image requests.")
    parser.add_argument("--transcription", choices=("assemblyai", "gemini"), default="assemblyai")
    parser.add_argument("--local-ocr", choices=("true", "false"), default="true")
    parser.add_argument("--local-page-control", action="store_true", help="Simulate retrieval of example.test control only; NOT public fetch validation.")
    parser.add_argument("--source-diagnostics", action="store_true", help="QA only: retain bounded public HTML/bodies locally and allow one read of each fixed Royal/UOL source; never model retries.")
    parser.add_argument("--container", action="store_true")
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--record-dir", required=True)
    return parser


def validate_arguments(parser, args):
    selected = {p.strip() for p in args.providers.split(",") if p.strip()}
    if not selected <= KEYS.keys() or not 1024 <= args.port <= 65535:
        parser.error("Unsupported provider/port.")
    if (selected or args.hive_paid_budget_approved) and not args.free_credits_confirmed:
        parser.error("Confirm free credits without automatic paid overage first.")
    if ("hive" in selected) != args.hive_paid_budget_approved:
        parser.error("Hive requires both explicit provider selection and paid-budget approval.")
    approved_models = {"gemini-3.7-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"}
    if args.gemini_model not in approved_models or args.media_model not in approved_models:
        parser.error("Only explicitly verified free-tier Gemini models are allowed by this test runner.")
    public_cap = args.public_fetch_cap if args.public_fetch_cap is not None else CAPS["public_fetch"]
    return selected, {**CAPS, "gemini": args.gemini_request_cap,
                      "public_fetch": public_cap, "sightengine": args.sightengine_request_cap}


def _integer(value, maximum):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum


def diagnostic_source_url(value):
    """Public curated HTTPS only; signed/query/fragment URLs are never retained."""
    if not isinstance(value, str) or not 1 <= len(value) <= 4096 or any(char.isspace() or ord(char) < 32 for char in value):
        return None
    import httpx
    from app.services.source_registry import source_family
    try:
        url = httpx.URL(value)
        if (url.scheme != "https" or url.userinfo or url.port not in {None, 443}
                or url.query or url.fragment or "?" in value or "#" in value
                or not source_family(str(url))):
            return None
        return str(url)
    except (httpx.InvalidURL, ValueError):
        return None


def diagnostic_document(value):
    """Only fixed public article fields, never response headers or raw errors."""
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("failure"), str) and value["failure"] in {"oversize", "unsupported_content", "blocked_or_unavailable", "timeout", "error"}:
        return {"failure": value["failure"]}
    url, sentences = diagnostic_source_url(value.get("url")), value.get("sentences")
    title, truncated, retrieved = value.get("title"), value.get("truncated"), value.get("retrieved_at")
    roles = value.get("sentence_roles")
    if (not url or not isinstance(sentences, list) or len(sentences) > 3000
            or any(not isinstance(item, str) for item in sentences) or sum(map(len, sentences)) > 50000
            or not isinstance(title, str) or len(title) > 300 or not isinstance(truncated, bool)
            or not isinstance(retrieved, str) or len(retrieved) > 60
            or not isinstance(roles, list) or len(roles) != len(sentences)
            or any(not isinstance(role, str) or role not in {"body", "context"} for role in roles)):
        return None
    try:
        if datetime.fromisoformat(retrieved).tzinfo is None:
            return None
    except ValueError:
        return None
    return {"url": url, "title": title, "sentences": sentences, "sentence_roles": roles,
            "truncated": truncated, "retrieved_at": retrieved}


class PublicSourceDiagnostics:
    """Task-owned v2 diagnostics scoped to four fixed public statements.

    Generic/private requests still use the app normally but leave no diagnostic
    query/body/document here. v1 records are preserved, not read or migrated.
    HTML files are exclusive; manifests resume, bounded and fail-closed.
    """
    MAX_RECORDS = 80
    MANIFEST_BYTES = 10 * 1024 * 1024
    SCOPES = {*DIAGNOSTIC_TEXT_CONTROLS, *("fixed:" + name for name in DIAGNOSTIC_FIXED_SOURCES)}

    def __init__(self, directory):
        self.directory = Path(directory)
        self.scope = ContextVar("verify_fixed_public_diagnostic_scope", default=None)
        self.records = {"bodies": [], "documents": [], "searches": []}
        self.paths = {name: self.directory / f"public-source-{name}-v2.json" for name in self.records}
        for name, path in self.paths.items():
            if not path.exists():
                continue
            if path.is_symlink() or path.stat().st_size > self.MANIFEST_BYTES:
                raise ValueError("Invalid local diagnostic manifest.")
            try:
                rows = json.loads(path.read_text())
            except (ValueError, OSError):
                raise ValueError("Invalid local diagnostic manifest.") from None
            if not isinstance(rows, list) or len(rows) > self.MAX_RECORDS or any(not self._valid_row(name, row) for row in rows):
                raise ValueError("Invalid local diagnostic records.")
            self.records[name] = rows
        expected = {row["file"] for row in self.records["bodies"]}
        if [row["file"] for row in self.records["bodies"]] != [f"source-body-v2-{index}.html" for index in range(1, len(expected) + 1)]:
            raise ValueError("Repeated or nonsequential diagnostic body reference.")
        observed = {path.name for path in self.directory.glob("source-body-v2-*.html")}
        if observed != expected:
            raise ValueError("Unmatched local diagnostic body; no overwrite or guessing.")
        for row in self.records["bodies"]:
            path = self.directory / row["file"]
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Invalid local diagnostic body.")

    def _valid_row(self, name, row):
        if not isinstance(row, dict) or not isinstance(row.get("scope"), str) or row["scope"] not in self.SCOPES:
            return False
        if name == "bodies":
            return (set(row) == {"scope", "requested_url", "final_url", "content_type", "encoding", "file"}
                and bool(diagnostic_source_url(row["requested_url"])) and bool(diagnostic_source_url(row["final_url"]))
                and isinstance(row["content_type"], str) and row["content_type"] in {"text/html", "application/xhtml+xml", "text/plain"}
                and isinstance(row["encoding"], str) and bool(re.fullmatch(r"[A-Za-z0-9._-]{1,40}", row["encoding"]))
                and isinstance(row["file"], str) and bool(re.fullmatch(r"source-body-v2-[1-9][0-9]{0,2}\.html", row["file"])))
        if name == "documents":
            return (set(row) == {"scope", "requested_url", "document"}
                and bool(diagnostic_source_url(row["requested_url"])) and isinstance(row["document"], dict)
                and diagnostic_document(row["document"]) is not None
                and diagnostic_document(row["document"]) == row["document"])
        return (set(row) == {"scope", "query_sha256", "status", "leads"}
            and isinstance(row["query_sha256"], str) and bool(re.fullmatch(r"[0-9a-f]{64}", row["query_sha256"]))
            and isinstance(row["status"], str) and row["status"] in {"success", "no_results", "not_configured", "not_requested", "timeout", "rate_limited", "error", "invalid_response"}
            and isinstance(row["leads"], list) and len(row["leads"]) <= 20
            and all(isinstance(lead, dict) and set(lead) == {"url"} and bool(diagnostic_source_url(lead["url"])) for lead in row["leads"]))

    def _persist(self, name):
        descriptor, temporary = tempfile.mkstemp(prefix="source-diagnostic-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(self.records[name], output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.paths[name])
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _append(self, name, row):
        if len(self.records[name]) >= self.MAX_RECORDS or not self._valid_row(name, row):
            raise ValueError("Diagnostic record unavailable or outside fixed public scope.")
        self.records[name].append(row)
        self._persist(name)

    async def run_scoped(self, original, scope, *args, **kwargs):
        token = self.scope.set(scope if scope in self.SCOPES else None)
        try:
            return await original(*args, **kwargs)
        finally:
            self.scope.reset(token)

    def record_fetch(self, requested_url, resource):
        scope = self.scope.get()
        if not scope:
            return
        requested, final = diagnostic_source_url(requested_url), diagnostic_source_url(resource.final_url)
        if not requested or not final:
            return
        if not isinstance(resource.data, bytes) or not 0 < len(resource.data) <= 2 * 1024 * 1024:
            raise ValueError("Diagnostic body outside bounded public scope.")
        index = len(self.records["bodies"]) + 1
        row = {"scope": scope, "requested_url": requested, "final_url": final, "content_type": resource.content_type,
               "encoding": resource.encoding, "file": f"source-body-v2-{index}.html"}
        if not self._valid_row("bodies", row) or len(self.records["bodies"]) >= self.MAX_RECORDS:
            raise ValueError("Invalid bounded public diagnostic body.")
        with (self.directory / row["file"]).open("xb") as output:
            output.write(resource.data)
            output.flush()
            os.fsync(output.fileno())
        self._append("bodies", row)

    def record_article(self, requested_url, result):
        scope = self.scope.get()
        if not scope:
            return
        url = diagnostic_source_url(requested_url)
        document = diagnostic_document(result)
        if scope and url and document is not None:
            self._append("documents", {"scope": scope, "requested_url": url, "document": document})

    def record_search(self, query, result):
        scope = self.scope.get()
        if not scope or not isinstance(query, str) or not 1 <= len(query) <= 500:
            return
        leads = []
        for lead in list(result)[:20]:
            url = diagnostic_source_url(lead.get("link") or lead.get("url")) if isinstance(lead, dict) else None
            if url:
                leads.append({"url": url})
        status = getattr(result, "status", "invalid_response")
        if status not in {"success", "no_results", "not_configured", "not_requested", "timeout", "rate_limited", "error", "invalid_response"}:
            status = "invalid_response"
        self._append("searches", {"scope": scope, "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                                 "status": status, "leads": leads})


def install_source_diagnostics(app, record_dir):
    from app.core import pipeline
    from app.services import source_attribution
    from fastapi import HTTPException
    diagnostics = PublicSourceDiagnostics(record_dir)

    original_fetch, original_article = source_attribution.fetch_public_resource, source_attribution._fetch_article
    original_search, original_retrieval = pipeline.search_web, pipeline._retrieve_source_attribution

    async def capture_fetch(url, **kwargs):
        resource = await original_fetch(url, **kwargs)
        diagnostics.record_fetch(url, resource)
        return resource

    async def capture_article(url):
        result = await original_article(url)
        diagnostics.record_article(url, result)
        return result

    async def capture_search(query):
        result = await original_search(query)
        diagnostics.record_search(query, result)
        return result

    async def capture_retrieval(text, *args, **kwargs):
        scope = next((name for name, statement in DIAGNOSTIC_TEXT_CONTROLS.items() if text == statement), None)
        return await diagnostics.run_scoped(original_retrieval, scope, text, *args, **kwargs)

    source_attribution.fetch_public_resource, source_attribution._fetch_article = capture_fetch, capture_article
    pipeline.search_web, pipeline._retrieve_source_attribution = capture_search, capture_retrieval

    @app.get("/__validation/source-control/{name}")
    async def source_control(name: str):
        if name not in DIAGNOSTIC_FIXED_SOURCES:
            raise HTTPException(404, "Unknown fixed control.")
        marker = Path(record_dir) / f"source-control-{name}.json"
        try:
            with marker.open("x", encoding="utf-8") as output:
                json.dump({"status": "started"}, output)
                output.flush()
                os.fsync(output.fileno())
        except FileExistsError:
            raise HTTPException(409, "Fixed diagnostic already attempted; no retry.") from None
        result = await diagnostics.run_scoped(capture_article, "fixed:" + name, DIAGNOSTIC_FIXED_SOURCES[name])
        document = diagnostic_document(result) or {"failure": "invalid_response"}
        marker.write_text(json.dumps(document, ensure_ascii=False, indent=2))
        return {"status": document.get("failure", "read"), "sentence_count": len(document.get("sentences", []))}
    return diagnostics


class ValidationBudgetJournal:
    """Single owned QA process, restart-safe reservations; never a provider bill.

    The local file lock prevents two QA processes sharing this folder. Atomic,
    fsynced replacement precedes network; a lost/failed write blocks sending.
    Paid admission is additional to, not a replacement for, production reserve.
    """
    def __init__(self, path, caps):
        self.path, self.caps = Path(path), dict(caps)
        self._mutex = threading.RLock()
        self._hive_permits = 0
        self._lock_file = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path.parent / "provider-budget.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            self._lock_file = os.fdopen(descriptor, "a+")
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.path.is_symlink():
                raise ValueError("Unusable QA journal.")
            existing = json.loads(self.path.read_text()) if self.path.exists() and self.path.stat().st_size <= 2 * 1024 * 1024 else {}
            if self.path.exists() and not existing:
                raise ValueError("Invalid existing QA journal.")
            self._load(existing)
            self.persist()
        except Exception:
            self.close()
            raise ValueError("QA budget journal unavailable or invalid; no provider request started.") from None

    def _load(self, existing):
        allowed = {"scope", "events", "counts", "caps", "asr_jobs", "hive_reservations", "hive_paid_caps"}
        if not isinstance(existing, dict) or not set(existing) <= allowed:
            raise ValueError("Invalid QA journal.")
        counts, events = existing.get("counts", {}), existing.get("events", [])
        if (not isinstance(counts, dict) or not set(counts) <= MAX_CAPS.keys()
                or any(not _integer(value, MAX_CAPS[key]) for key, value in counts.items())
                or not isinstance(events, list) or len(events) > 256):
            raise ValueError("Invalid QA counters.")
        recorded_caps = existing.get("caps", {})
        if (not isinstance(recorded_caps, dict) or not set(recorded_caps) <= MAX_CAPS.keys()
                or any(not _integer(value, MAX_CAPS[key]) for key, value in recorded_caps.items())
                or existing.get("hive_paid_caps", HIVE_QA_CAPS) != HIVE_QA_CAPS):
            raise ValueError("Invalid QA ceilings.")
        seen = Counter()
        for event in events:
            if (not isinstance(event, dict) or not set(event) <= {"provider", "request_number", "method", "http_status", "transport_status"}
                    or event.get("provider") not in MAX_CAPS or event.get("method") not in {"GET", "POST", "HEAD", "OPTIONS"}
                    or event.get("transport_status", "reserved") not in {"reserved", "incomplete"}
                    or ("http_status" in event and not _integer(event["http_status"], 599))):
                raise ValueError("Invalid QA event.")
            provider = event["provider"]
            seen[provider] += 1
            if event.get("request_number") != seen[provider] or isinstance(event.get("request_number"), bool):
                raise ValueError("Invalid QA event count.")
        if any(seen[key] != value for key, value in counts.items()) or any(counts.get(key, 0) != value for key, value in seen.items()):
            raise ValueError("Inconsistent QA counter.")
        old_posts = sum(e["provider"] == "assemblyai" and e["method"] == "POST" for e in events)
        jobs = existing.get("asr_jobs", {"upload": (old_posts + 1) // 2, "job": old_posts // 2})
        if not isinstance(jobs, dict) or not set(jobs) <= {"upload", "job"} or any(not _integer(value, 2) for value in jobs.values()):
            raise ValueError("Invalid QA ASR counter.")
        hive = existing.get("hive_reservations", {key: 0 for key in HIVE_QA_CAPS})
        if (not isinstance(hive, dict) or set(hive) != set(HIVE_QA_CAPS)
                or any(not _integer(hive[key], maximum) for key, maximum in HIVE_QA_CAPS.items())
                or bool(hive["audio_seconds"]) != bool(hive["audio_jobs"])
                or counts.get("hive", 0) > hive["image_requests"] + hive["audio_jobs"]):
            raise ValueError("Invalid or missing Hive paid reservation.")
        self.counts, self.events, self.jobs, self.hive = Counter(counts), events, Counter(jobs), dict(hive)

    def close(self):
        if self._lock_file is not None:
            self._lock_file.close()
            self._lock_file = None

    def persist(self):
        with self._mutex:
            data = {"scope": "transport, NOT accuracy", "events": self.events,
                    "counts": dict(self.counts), "caps": self.caps, "asr_jobs": dict(self.jobs),
                    "hive_reservations": self.hive, "hive_paid_caps": HIVE_QA_CAPS}
            descriptor, name = tempfile.mkstemp(prefix="provider-journal-", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    json.dump(data, output, ensure_ascii=False, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(name, self.path)
                directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if os.path.exists(name):
                    os.unlink(name)

    def reserve_hive(self, original, media_type, duration_seconds=None):
        with self._mutex:
            units = 1
            if media_type == "audio":
                if (type(duration_seconds) not in {int, float} or not math.isfinite(duration_seconds)
                        or not 0 < duration_seconds <= 120):
                    return original(media_type, duration_seconds)
                units = math.ceil(duration_seconds)
            elif media_type != "image":
                return original(media_type, duration_seconds)
            field = "image_requests" if media_type == "image" else "audio_seconds"
            if (self.hive[field] + units > HIVE_QA_CAPS[field]
                    or media_type == "audio" and self.hive["audio_jobs"] >= HIVE_QA_CAPS["audio_jobs"]):
                return {"available": False, "status": "budget_exhausted", "api_version": "v3",
                        "reason": "Limite persistente da validação Hive atingido; nenhum arquivo foi enviado."}
            rejected = original(media_type, duration_seconds)
            if rejected is not None:
                return rejected
            self.hive[field] += units
            if media_type == "audio":
                self.hive["audio_jobs"] += 1
            self.persist()
            self._hive_permits += 1
            return None

    def reserve_send(self, provider, method, *, asr_category=None):
        with self._mutex:
            if self.counts[provider] >= self.caps[provider]:
                raise ValueError("Validation request cap reached.")
            if asr_category:
                if self.jobs[asr_category] >= 2:
                    raise ValueError("Validation ASR job cap reached.")
                self.jobs[asr_category] += 1
            if provider == "hive":
                if self._hive_permits <= 0:
                    raise ValueError("Hive has no new paid reservation.")
                self._hive_permits -= 1
            self.counts[provider] += 1
            event = {"provider": provider, "request_number": self.counts[provider], "method": method,
                     "transport_status": "reserved"}
            self.events.append(event)
            self.persist()
            return event


def main():
    parser = build_parser()
    args = parser.parse_args()
    selected, caps = validate_arguments(parser, args)
    record_dir = Path(args.record_dir)
    try:
        budget = ValidationBudgetJournal(record_dir / "provider-transport.json", caps)
    except ValueError:
        parser.error("QA budget journal unavailable or invalid; no provider request started.")
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    import dotenv
    private = dotenv.dotenv_values(args.env_file, interpolate=False)
    # Clear inherited secrets before importing any clients with static config.
    for key in list(os.environ):
        if "API_KEY" in key or "API_TOKEN" in key or key in {"SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"}:
            os.environ.pop(key, None)
    for name in selected:
        for key in KEYS[name]:
            os.environ[key] = private.get(key) or ""
    dotenv.load_dotenv = lambda *_args, **_kwargs: False
    private.clear()
    runtime = Path(tempfile.mkdtemp(prefix="verify-ui-validation-"))
    os.environ.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{runtime / 'validation.db'}",
        "APP_ENV": "development", "COOKIE_SECURE": "false", "COOKIE_SAME_SITE": "lax",
        "JWT_SECRET": secrets.token_urlsafe(48), "HMAC_SECRET_KEY": secrets.token_urlsafe(48),
        "CORS_ORIGINS": "http://127.0.0.1:5176,http://localhost:5176",
        "CORS_ORIGIN_REGEX": "", "PYTHON_DOTENV_DISABLED": "1",
        "ANALYSIS_REQUESTS_PER_MINUTE": "100", "ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE": "200",
        "GEMINI_MODEL_NAME": args.gemini_model, "GEMINI_MEDIA_MODEL_NAME": args.media_model,
        "GEMINI_FALLBACK_MODELS": "", "OPENROUTER_MODEL": "openrouter/free",
        "OPENROUTER_FALLBACK_MODELS": "", "OPENROUTER_DAILY_LIMIT": "9",
        "OPENROUTER_ENABLED": "true" if "openrouter" in selected else "false",
        "AUDIO_TRANSCRIPTION_PROVIDER": args.transcription, "LOCAL_OCR_ENABLED": args.local_ocr,
        "HIVE_API_VERSION": "v3", "HIVE_V3_MEDIA_TYPES": "image,audio" if "hive" in selected else "",
        "HIVE_V3_IMAGE_REQUEST_LIMIT": "2" if "hive" in selected else "0",
        "HIVE_V3_AUDIO_SECONDS_LIMIT": "5" if "hive" in selected else "0",
        "VIDEO_MAX_FRAMES": "3", "SIGHTENGINE_AUDIO_ENABLED": "false", "HUGGINGFACE_ENABLED": "false",
        "GOOGLE_CLIENT_ID": "", "WAYBACK_API_ENABLED": "false", "C2PATOOL_ENABLED": "false",
        "HUGGINGFACE_IMAGE_API_URL": "https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector" if "hf" in selected else "",
        "HUGGINGFACE_AI_LABEL": "ai", "EXIFTOOL_ENABLED": "true",
    })
    import httpx
    original_send = httpx.AsyncClient.send
    if "hive" in selected:
        from app.services.hive_service import hive_v3_budget
        original_reserve = hive_v3_budget.reserve
        hive_v3_budget.reserve = lambda media_type, duration_seconds=None: budget.reserve_hive(original_reserve, media_type, duration_seconds)

    async def bounded_send(client, request, *pos, **kw):
        provider = request_provider(request)
        if provider is None or provider not in selected:
            raise httpx.RequestError("Validation outbound provider blocked", request=request)
        category = None
        if provider == "assemblyai" and request.method == "POST":
            # At most two audio uploads/jobs. Polling cannot create new jobs.
            category = "upload" if request.url.path.endswith("/upload") else "job"
        try:
            event = budget.reserve_send(provider, request.method, asr_category=category)
        except (ValueError, OSError):
            raise httpx.RequestError("Validation outbound budget unavailable or exhausted", request=request) from None
        try:
            response = await original_send(client, request, *pos, **kw)
            event.pop("transport_status", None)
            event["http_status"] = response.status_code
            return response
        except BaseException:
            event["transport_status"] = "incomplete"
            raise
        finally:
            budget.persist()  # No URL/query/headers, IDs, media, bodies or keys.

    httpx.AsyncClient.send = bounded_send
    from app.main import app
    if args.source_diagnostics:
        install_source_diagnostics(app, record_dir)
    # QA boundary evidence only: never capture bodies, query strings, cookies,
    # account identifiers or signed capabilities. Not installed in production.
    http_events = []
    observed_paths = {"/api/check-text", "/api/check-url", "/api/check-extracted-text",
                      "/api/upload", "/api/verificar/relatorio-pdf"}

    @app.middleware("http")
    async def record_validation_boundary(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path in observed_paths:
            http_events.append({"path": path, "method": request.method, "status": response.status_code,
                                "content_type": response.headers.get("content-type", ""),
                                "cache_control": response.headers.get("cache-control", "")})
            (record_dir / "http-boundaries.json").write_text(json.dumps({
                "scope": "local UI HTTP boundaries, NOT provider accuracy", "events": http_events,
            }, indent=2), encoding="utf-8")
        return response

    if args.local_page_control:
        from app.api import check_url
        check_url.fetch_public_resource = local_page_control_fetch(check_url.fetch_public_resource)
    from app.core.database import init_db, AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserTier
    import uvicorn

    async def seed():
        await init_db()
        async with AsyncSessionLocal() as db:
            db.add(User(email="validation@example.test", name="Validação local",
                        hashed_password=hash_password("Local-Test-Only-938!"), tier=UserTier.ENTERPRISE))
            await db.commit()

    asyncio.run(seed())
    (record_dir / "configuration.json").write_text(json.dumps({
        "started_at": datetime.now(timezone.utc).isoformat(), "providers": sorted(selected),
        "gemini_model": args.gemini_model, "media_model": args.media_model,
        "transcription": args.transcription, "local_ocr": args.local_ocr,
        "caps": caps, "video_max_frames": 3,
        "source_diagnostics": {"enabled": args.source_diagnostics, "version": 2, "fixed_public_inputs_only": True},
        "hive": {"enabled": "hive" in selected, "existing_credit_approved": args.hive_paid_budget_approved,
                 "caps": HIVE_QA_CAPS, "nominal_price_ceiling_usd": .0258888889,
                 "price_is_not_a_billing_statement": True, "no_retries": True},
        "database": "disposable_local",
        "local_page_control": {"enabled": args.local_page_control, "url": LOCAL_PAGE_CONTROL_URL,
                               "scope": "simulated HTTP from local fixture, NOT a public HTTPS integration"},
    }, indent=2), encoding="utf-8")
    print("UI validation: disposable DB, curated providers, persistent hard outbound caps.", flush=True)
    try:
        uvicorn.run(app, host="0.0.0.0" if args.container else "127.0.0.1", port=args.port, access_log=False)
    finally:
        budget.close()


if __name__ == "__main__":
    main()
