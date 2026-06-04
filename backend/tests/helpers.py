import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://verifai:verifai_pass@localhost:5432/verifai_test")

from app.core.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import UserTier


def fake_report(**overrides):
    report = {
        "score": 72,
        "semantic_score": 70,
        "domain_score": 80,
        "sensationalism": 10,
        "verdict": "Suspicious",
        "summary": "Automated audit finished.",
        "red_flags": [],
        "positive_signals": ["Corroborated context"],
        "logical_fallacies": [],
        "emotional_triggers": False,
        "fact_checks": [],
        "domain_note": "No domain provided",
        "source_url": None,
        "recommended_sources": [],
    }
    report.update(overrides)
    return report


def fake_user(**overrides):
    user = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "name": "Test User",
        "tier": UserTier.STANDARD,
        "avatar_url": None,
        "is_active": True,
    }
    user.update(overrides)
    return SimpleNamespace(**user)


class ScalarResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, execute_results=None):
        self.added = []
        self.deleted = []
        self.commits = 0
        self.flushes = 0
        self.execute_results = list(execute_results or [])

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        self.flushes += 1
        for instance in self.added:
            if getattr(instance, "id", None) is None and hasattr(instance, "id"):
                instance.id = uuid.uuid4()

    async def commit(self):
        self.commits += 1

    async def refresh(self, _instance):
        return None

    async def execute(self, _statement):
        if self.execute_results:
            return self.execute_results.pop(0)
        return ScalarResult()

    async def delete(self, instance):
        self.deleted.append(instance)


def override_auth_and_db(user, db):
    async def current_user_override():
        return user

    async def db_override():
        yield db

    app.dependency_overrides[get_current_user] = current_user_override
    app.dependency_overrides[get_db] = db_override
