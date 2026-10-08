import asyncio
import os
import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from pathlib import Path

from helpers import app, fake_report
from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.models.history import ContentType, Verification, VerdictLabel
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


if __name__ == "__main__":
    unittest.main()
