"""Cheap database connectivity check; never probes external AI providers."""
import asyncio
import time

from sqlalchemy import text


class DatabaseReadiness:
    """Coalesce health probes per process, with a short result cache and deadline.

    SELECT 1 checks connectivity, not schema migration, writable transactions,
    quotas or model quality. Neither exception text nor DB URLs are returned.
    """

    def __init__(self, engine, *, timeout_seconds=2.0, cache_seconds=2.0):
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = cache_seconds
        self._lock = asyncio.Lock()
        self._expires_at = 0.0
        self._status = "unavailable"

    async def check(self) -> str:
        if time.monotonic() < self._expires_at:
            return self._status
        try:
            # Deadline includes waiting for a concurrent probe and connection
            # acquisition, not just the SQL query. Cancellation propagates.
            async with asyncio.timeout(self.timeout_seconds):
                async with self._lock:
                    if time.monotonic() < self._expires_at:
                        return self._status
                    try:
                        async with self.engine.connect() as conn:
                            result = await conn.execute(text("SELECT 1"))
                            status = "ok" if result.scalar_one() == 1 else "unavailable"
                    except Exception:
                        # Do not leak driver errors, credentials, hosts or SQL.
                        status = "unavailable"
                    self._status = status
                    self._expires_at = time.monotonic() + self.cache_seconds
                    return status
        except TimeoutError:
            # A timed-out waiter must not overwrite a running probe's result.
            return "timeout"
