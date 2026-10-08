import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from helpers import app
from app.services.readiness import DatabaseReadiness


class FakeEngine:
    def __init__(self, value=1, *, error=None, connect_delay=0, query_delay=0):
        self.value = value
        self.error = error
        self.connect_delay = connect_delay
        self.query_delay = query_delay
        self.connections = 0
        self.closed = 0
        self.statements = []

    @asynccontextmanager
    async def connect(self):
        self.connections += 1
        await asyncio.sleep(self.connect_delay)
        if self.error:
            raise self.error
        try:
            yield self
        finally:
            self.closed += 1

    async def execute(self, statement):
        self.statements.append(str(statement))
        await asyncio.sleep(self.query_delay)
        return self

    def scalar_one(self):
        return self.value


class ReadinessServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_disposable_sqlite_database(self):
        with tempfile.TemporaryDirectory(prefix="verify-ready-test-") as directory:
            engine = create_async_engine(f"sqlite+aiosqlite:///{Path(directory) / 'ready-test.db'}")
            try:
                self.assertEqual(await DatabaseReadiness(engine).check(), "ok")
            finally:
                await engine.dispose()

    async def test_probe_is_read_only_and_closes_connection(self):
        engine = FakeEngine()
        self.assertEqual(await DatabaseReadiness(engine).check(), "ok")
        self.assertEqual(engine.statements, ["SELECT 1"])
        self.assertEqual(engine.closed, 1)

    async def test_simultaneous_requests_share_single_query(self):
        engine = FakeEngine(query_delay=.01)
        probe = DatabaseReadiness(engine)
        results = await asyncio.gather(*(probe.check() for _ in range(20)))
        self.assertEqual(results, ["ok"] * 20)
        self.assertEqual(engine.connections, 1)

    async def test_expired_negative_cache_can_recover(self):
        engine = FakeEngine(error=RuntimeError("private-password-host"))
        probe = DatabaseReadiness(engine)
        self.assertEqual(await probe.check(), "unavailable")
        engine.error = None
        self.assertEqual(await probe.check(), "unavailable")
        self.assertEqual(engine.connections, 1)
        probe._expires_at = time.monotonic() - 1
        self.assertEqual(await probe.check(), "ok")
        self.assertEqual(engine.connections, 2)

    async def test_deadline_includes_connection_and_query(self):
        for mode in ("connect_delay", "query_delay"):
            with self.subTest(mode=mode):
                engine = FakeEngine(**{mode: 1})
                started = time.monotonic()
                self.assertEqual(await DatabaseReadiness(engine, timeout_seconds=.02).check(), "timeout")
                self.assertLess(time.monotonic() - started, .5)
                if mode == "query_delay":
                    self.assertEqual(engine.closed, 1)

    async def test_unexpected_scalar_is_not_ready(self):
        self.assertEqual(await DatabaseReadiness(FakeEngine(value=0)).check(), "unavailable")

    async def test_cancellation_propagates_and_connection_is_released(self):
        engine = FakeEngine(query_delay=1)
        task = asyncio.create_task(DatabaseReadiness(engine).check())
        while not engine.statements:
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(engine.closed, 1)


class ReadinessEndpointTests(unittest.TestCase):
    def test_http_contract_and_no_cache_on_failure_or_success(self):
        with TestClient(app) as client, patch("app.main.readiness_probe") as probe:
            probe.check = AsyncMock()
            for status in ("ok", "unavailable", "timeout"):
                with self.subTest(status=status):
                    probe.check.return_value = status
                    response = client.get("/ready")
                    self.assertEqual(response.status_code, 200 if status == "ok" else 503)
                    self.assertEqual(response.json(), {
                        "status": "ready" if status == "ok" else "not_ready",
                        "service": "Verify", "checks": {"database": status},
                    })
                    self.assertEqual(response.headers["cache-control"], "no-store")

    def test_liveness_never_uses_database_or_providers(self):
        with TestClient(app) as client, patch("app.main.readiness_probe") as probe:
            probe.check = AsyncMock(side_effect=AssertionError("Readiness called by liveness"))
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "Verify"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        probe.check.assert_not_awaited()
