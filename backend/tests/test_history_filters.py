"""History queries run offline in an isolated, automatically discarded SQLite DB."""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import select

from helpers import app
from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.models.history import ContentType, Verification, VerdictLabel
from app.models.user import User, UserTier
from app.services.pdf_snapshot import verify_pdf_snapshot


class HistoryFiltersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="verify-history-tests-")
        db_path = Path(cls.directory.name) / "history-test.db"
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)
        cls.Session = async_sessionmaker(cls.engine, expire_on_commit=False)
        asyncio.run(cls._create_schema())

    @classmethod
    async def _create_schema(cls):
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        cls.directory.cleanup()

    def setUp(self):
        self.client = TestClient(app)
        asyncio.run(self._seed_data())

        async def current_user():
            return self.user

        async def db_override():
            async with self.Session() as session:
                yield session

        app.dependency_overrides[get_current_user] = current_user
        app.dependency_overrides[get_db] = db_override

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    async def _seed_data(self):
        self.user = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.test", name="Dono A",
                         hashed_password="not-used", tier=UserTier.STANDARD)
        other = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.test", name="Dono B",
                     hashed_password="not-used", tier=UserTier.STANDARD)
        created = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
        kinds = (ContentType.TEXT, ContentType.TEXT, ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO)
        verdicts = (VerdictLabel.SUSPICIOUS, VerdictLabel.FALSE, VerdictLabel.AUTHENTIC)
        self.row_ids = set()
        async with self.Session() as session:
            session.add_all([self.user, other])
            await session.flush()
            for index in range(45):
                raw = {"query_input": f"Consulta {index}", "filename": f"arquivo-{index}.bin"}
                url = f"https://example.com/item-{index}" if index % 5 == 1 else None
                if index == 0:
                    raw["query_input"] = "Desconto 50% aprovado"
                    raw["analysis_status"] = "inconclusive"
                elif index == 1:
                    url = "https://example.com/manual_01"
                elif index == 2:
                    raw["filename"] = "foto_final_02.png"
                    raw.update({"content_type": "image", "file_hash_sha256": "a" * 64,
                        "verdict": "Authentic", "summary": "Resumo de teste 2", "plain_explanation": "Controle salvo.",
                        "elderly_tip": "Confira as fontes.", "forensics": {}})
                elif index == 3:
                    raw["query_input"] = r"C:\controle\amostra"
                row_id = uuid.uuid4()
                if index == 0:
                    self.legacy_id = row_id
                if index == 2:
                    self.media_id = row_id
                self.row_ids.add(str(row_id))
                session.add(Verification(id=row_id, user_id=self.user.id, content_type=kinds[index % 5],
                    source_url=url, verdict_score=70, verdict_label=verdicts[index % 3],
                    ai_summary=f"Resumo de teste {index}", raw_result=raw,
                    created_at=created + timedelta(seconds=index)))
            self.other_id = uuid.uuid4()
            session.add(Verification(id=self.other_id, user_id=other.id, content_type=ContentType.VIDEO,
                verdict_score=70, verdict_label=VerdictLabel.FALSE,
                ai_summary="SEGREDO OUTRA CONTA 50% _ aprovado controle",
                raw_result={"query_input": "SEGREDO OUTRA CONTA"}, created_at=created))
            await session.commit()

    def history(self, **params):
        response = self.client.get("/api/history", params=params)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("SEGREDO OUTRA CONTA", response.text)
        return response.json()

    def test_45_rows_have_three_consistent_pages_with_no_duplicates(self):
        seen = []
        for page, expected in ((1, 20), (2, 20), (3, 5)):
            body = self.history(page=page)
            self.assertEqual((body["total"], body["page"], body["limit"]), (45, page, 20))
            self.assertEqual(len(body["items"]), expected)
            seen.extend(row["id"] for row in body["items"])
        self.assertEqual(set(seen), self.row_ids)
        self.assertEqual(len(set(seen)), len(seen))
        self.assertEqual(self.history(page=4)["items"], [])

    def test_type_filters_distinguish_links_and_include_video(self):
        for kind in ("Text", "Url", "Image", "Audio", "Video"):
            with self.subTest(kind=kind):
                body = self.history(content_type=kind)
                self.assertEqual(body["total"], 9)
                self.assertEqual(len(body["items"]), 9)
                self.assertEqual({row["content_type"] for row in body["items"]}, {kind})

    def test_verdict_filters_apply_before_pagination_and_combine_with_type(self):
        body = self.history(verdict="False", limit=5)
        self.assertEqual((body["total"], len(body["items"])), (15, 5))
        self.assertTrue(all(row["verdict_label"] == "False" for row in body["items"]))
        videos = self.history(content_type="Video", verdict="False")
        self.assertEqual(videos["total"], 3)
        self.assertTrue(all(row["content_type"] == "Video" for row in videos["items"]))

    def test_search_is_global_and_percent_underscore_backslash_are_literal(self):
        for term, expected in (("%", 1), ("_", 2), ("\\", 1), ("  APROVADO  ", 1),
                               ("foto_final_02", 1), ("Resumo de teste 44", 1),
                               ("' OR 1=1 --", 0), ("SEGREDO OUTRA CONTA", 0)):
            with self.subTest(term=term):
                body = self.history(search=term)
                self.assertEqual(body["total"], expected)
                self.assertEqual(len(body["items"]), expected)
        self.assertEqual(self.history(content_type="Video", search="Resumo de teste 44")["total"], 1)
        self.assertEqual(self.history(content_type="Text", search="Resumo de teste 44")["total"], 0)

    def test_inconclusive_index_remains_hidden(self):
        row = self.history(search="50%")["items"][0]
        self.assertEqual(row["analysis_status"], "inconclusive")
        self.assertIsNone(row["verdict_score"])

    def test_unversioned_and_inconclusive_history_has_no_average_index(self):
        response = self.client.get("/api/history/stats")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 45)
        self.assertIsNone(body["avg_score"])
        self.assertEqual(body["avg_score_count"], 0)

    def test_average_counts_only_documented_partial_indices_and_preserves_zero(self):
        async def add_indices():
            async with self.Session() as session:
                for score, status, semantics in ((0, "partial", "legacy_decision_index_not_probability"),
                         (100, "partial", "legacy_decision_index_not_probability"),
                         (50, "inconclusive", "legacy_decision_index_not_probability"),
                         (90, "partial", "unknown"), (999, "partial", "legacy_decision_index_not_probability")):
                    session.add(Verification(user_id=self.user.id, content_type=ContentType.TEXT,
                        verdict_score=score, verdict_label=VerdictLabel.SUSPICIOUS, ai_summary="Controle de agregação",
                        raw_result={"analysis_status": status, "score_semantics": semantics}))
                await session.commit()
        asyncio.run(add_indices())
        body = self.client.get("/api/history/stats").json()
        self.assertEqual(body["total"], 50)
        self.assertEqual(body["avg_score"], 50.0)
        self.assertEqual(body["avg_score_count"], 2)
        self.assertEqual(body["avg_score_semantics"], "legacy_decision_index_not_probability")

    def test_malformed_legacy_report_does_not_break_the_history_page(self):
        async def replace_report(value):
            async with self.Session() as session:
                row = await session.get(Verification, self.legacy_id)
                row.raw_result = value
                await session.commit()

        for value in (None, "legacy serialized report", [], ["legacy item"]):
            with self.subTest(value=value):
                asyncio.run(replace_report(value))
                body = self.history(limit=50)
                row = next(item for item in body["items"] if item["id"] == str(self.legacy_id))
                self.assertEqual(row["query_input"], "Resumo de teste 0")
                self.assertIsNone(row["analysis_status"])
                self.assertIsNone(row["veracity_status"])

    def test_filters_and_offset_are_bounded(self):
        for params in ({"page": 0}, {"page": 10001}, {"limit": 0}, {"limit": 51},
                       {"search": "a" * 201}, {"content_type": "Unknown"}, {"verdict": "Unknown"}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/api/history", params=params).status_code, 422)

    def test_history_requires_auth_and_other_users_report_is_not_found(self):
        self.assertEqual(self.client.get(f"/api/history/{self.other_id}").status_code, 404)
        app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.get("/api/history").status_code, 401)

    def test_malformed_report_ids_are_rejected_before_the_guid_binder(self):
        for invalid in ("not-a-uuid", "0000", "00000000-0000-0000-0000-00000000000g"):
            with self.subTest(invalid=invalid):
                response = self.client.get(f"/api/history/{invalid}")
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get(f"/api/history/{uuid.uuid4()}").status_code, 404)

    def test_owned_media_can_export_saved_report_without_persisting_a_token(self):
        response = self.client.get(f"/api/history/{self.media_id}")
        self.assertEqual(response.status_code, 200)
        report = response.json()["raw_result"]
        self.assertEqual(report["pdf_export_status"], "ready")
        verified = verify_pdf_snapshot(report["pdf_snapshot_token"], self.user)
        self.assertEqual(verified["file_hash_sha256"], "a" * 64)
        self.assertEqual(verified["summary"], "Resumo de teste 2")
        self.assertEqual(verified["filename"], "foto_final_02.png")

        async def persisted_report():
            async with self.Session() as session:
                row = (await session.execute(select(Verification).where(Verification.id == self.media_id))).scalar_one()
                return row.raw_result

        self.assertFalse(any(key.startswith("pdf_") for key in asyncio.run(persisted_report())))
        legacy = self.client.get(f"/api/history/{self.legacy_id}").json()["raw_result"]
        self.assertEqual(legacy["pdf_export_status"], "unavailable")
        self.assertNotIn("pdf_snapshot_token", legacy)


if __name__ == "__main__":
    unittest.main()
