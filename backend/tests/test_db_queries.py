import asyncio
import os
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from pathlib import Path

from helpers import app, fake_report
from app.core.auth import get_current_user, get_optional_user
from app.core.database import Base, get_db
from app.models.history import AnalysisMetrics, ContentType, Verification, VerdictLabel
from app.models.user import User, UserTier
from app.services.readiness import DatabaseReadiness


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "Set TEST_DATABASE_URL for real DB query integration tests.")
class DbQueryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_name = Path(make_url(TEST_DATABASE_URL).database or "").name.lower()
        if "test" not in database_name:
            raise unittest.SkipTest("TEST_DATABASE_URL must point to a test database.")
        # asyncio.run and TestClient use different event loops. Never reuse an
        # asyncpg pooled connection across those loops; production keeps its pool.
        cls.engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
        cls.Session = async_sessionmaker(cls.engine, expire_on_commit=False)
        asyncio.run(cls._create_schema())

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls._drop_schema())
        asyncio.run(cls.engine.dispose())

    @classmethod
    async def _create_schema(cls):
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def _drop_schema(cls):
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def setUp(self):
        self.client = TestClient(app)
        self.user_id = uuid.uuid4()
        asyncio.run(self._seed_data())

        async def current_user_override():
            return self.user

        async def db_override():
            async with self.Session() as session:
                yield session

        app.dependency_overrides[get_current_user] = current_user_override
        app.dependency_overrides[get_optional_user] = current_user_override
        app.dependency_overrides[get_db] = db_override

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    async def _seed_data(self):
        async with self.Session() as session:
            self.user = User(
                id=self.user_id,
                email=f"{self.user_id}@example.com",
                hashed_password="not-used",
                name="Real DB User",
                tier=UserTier.STANDARD,
            )
            first = Verification(
                user_id=self.user_id,
                content_type=ContentType.TEXT,
                verdict_score=80,
                verdict_label=VerdictLabel.SUSPICIOUS,
                ai_summary="First saved audit",
                raw_result=fake_report(score=80, analysis_status="partial", score_semantics="legacy_decision_index_not_probability"),
            )
            second = Verification(
                user_id=self.user_id,
                content_type=ContentType.TEXT,
                source_url="https://example.com/story",
                verdict_score=60,
                verdict_label=VerdictLabel.AUTHENTIC,
                ai_summary="Second saved audit",
                raw_result=fake_report(score=60, verdict="Authentic", analysis_status="partial", score_semantics="legacy_decision_index_not_probability"),
            )
            session.add(self.user)
            # No ORM relationship orders these objects; PostgreSQL enforces the
            # FK immediately (SQLite's default test connection did not).
            await session.flush()
            session.add(first)
            session.add(second)
            await session.commit()

    def test_history_lists_rows_from_real_database(self):
        response = self.client.get("/api/history?limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["limit"], 10)
        self.assertEqual(len(body["items"]), 2)

    def test_stats_calculates_counts_and_average_from_real_database(self):
        response = self.client.get("/api/history/stats")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["daily_used"], 2)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["avg_score"], 70.0)
        self.assertEqual(body["avg_score_count"], 2)
        self.assertEqual(body["plan"], UserTier.STANDARD.value)

    def test_readiness_connects_to_real_test_database(self):
        self.assertEqual(asyncio.run(DatabaseReadiness(self.engine).check()), "ok")

    def test_url_search_date_persists_in_real_database(self):
        from sqlalchemy import select
        async def saved_date():
            async with self.Session() as session:
                result = await session.execute(select(AnalysisMetrics).join(Verification)
                    .where(Verification.user_id == self.user_id))
                return result.scalar_one().earliest_known_date
        for date_value in ("2026-10-03T09:30:00-03:00", "2 hours ago"):
            with self.subTest(date_value=date_value):
                result = {"report": fake_report(), "metrics": {"text_ai_probability": None,
                          "earliest_known_date": date_value}, "fact_checks": []}
                with patch("app.api.check_url.verify_limit", new=AsyncMock()), \
                     patch("app.api.check_url.fetch_page_text", new=AsyncMock(return_value={
                         "text": "Página de controle não pessoal com conteúdo suficiente para testar a gravação da análise.",
                         "final_url": "https://example.com/control"})), \
                     patch("app.api.check_url.run_pipeline", new=AsyncMock(return_value=result)):
                    response = self.client.post("/api/check-url", json={"url": "https://example.com/control"})
                self.assertEqual(response.status_code, 200)
                actual = asyncio.run(saved_date())
                if date_value == "2 hours ago":
                    self.assertIsNone(actual)
                else:
                    # SQLite loses timezone info; PostgreSQL must keep it.
                    self.assertEqual(actual.replace(tzinfo=timezone.utc), datetime(2026, 10, 3, 12, 30, tzinfo=timezone.utc))
                async def clear_metrics():
                    from sqlalchemy import delete
                    async with self.Session() as session:
                        await session.execute(delete(AnalysisMetrics).where(AnalysisMetrics.verification_id.in_(
                            select(Verification.id).where(Verification.user_id == self.user_id))))
                        await session.commit()
                asyncio.run(clear_metrics())


if __name__ == "__main__":
    unittest.main()
