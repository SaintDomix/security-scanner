"""
conftest.py  —  backend/tests/conftest.py
"""

import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_pytest.db"
os.environ["SECRET_KEY"]   = "test-secret-key-for-pytest-32chars!"
os.environ["ALGORITHM"]    = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.database import get_db
from app.models.models import Base

TEST_DB_URL = "sqlite:///./test_pytest.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if os.path.exists("test_pytest.db"):
            os.remove("test_pytest.db")
    except PermissionError:
        pass  # Windows may keep the file locked briefly — safe to ignore


@pytest.fixture(scope="function")
def db():
    """
    Direct DB session for unit tests that don't go through HTTP.
    Uses its own connection — do NOT mix this with client calls in the same test,
    because SQLite will deadlock (two writers on the same file).
    """
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def registered_user(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = {
        "email":     f"auto_{uid}@test.com",
        "username":  f"auto_{uid}",
        "password":  "SecurePass123!",
        "full_name": "Auto Tester",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, f"Fixture registration failed: {resp.text}"
    data = resp.json()
    return {
        "token":    data["access_token"],
        "email":    payload["email"],
        "username": payload["username"],
        "password": payload["password"],
        "user":     data["user"],
    }


@pytest.fixture(scope="module")
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['token']}"}
