"""
test_auth.py  —  backend/tests/test_auth.py
Tests for POST /api/auth/register  and  POST /api/auth/login
"""

import uuid
import pytest


def new_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "email":    f"u_{uid}@test.com",
        "username": f"u_{uid}",
        "password": "TestPass123!",
    }


# ── Registration ──────────────────────────────────────────────────────────────

def test_TC01_valid_registration_returns_token(client):
    resp = client.post("/api/auth/register", json=new_user())
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data


def test_TC02_duplicate_email_returns_400(client):
    user = new_user()
    client.post("/api/auth/register", json=user)
    user2 = user.copy()
    user2["username"] = "other_" + uuid.uuid4().hex[:6]
    resp = client.post("/api/auth/register", json=user2)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


def test_TC03_duplicate_username_returns_400(client):
    user = new_user()
    client.post("/api/auth/register", json=user)
    user2 = user.copy()
    user2["email"] = "other_" + uuid.uuid4().hex[:6] + "@test.com"
    resp = client.post("/api/auth/register", json=user2)
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"].lower()


def test_TC04_missing_username_returns_422(client):
    resp = client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "Pass123!"
    })
    assert resp.status_code == 422


def test_TC05_invalid_email_format_returns_422(client):
    resp = client.post("/api/auth/register", json={
        "email": "not-an-email", "username": "user1", "password": "Pass123!"
    })
    assert resp.status_code == 422


def test_TC06_registered_user_data_matches_payload(client):
    user = new_user()
    user["full_name"] = "Full Name Test"
    resp = client.post("/api/auth/register", json=user)
    assert resp.status_code == 200
    u = resp.json()["user"]
    assert u["email"]             == user["email"]
    assert u["username"]          == user["username"]
    assert u["full_name"]         == "Full Name Test"
    assert u["subscription_tier"] == "free"
    assert u["scans_today"]       == 0
    assert "password"        not in u
    assert "hashed_password" not in u


def test_TC07_token_has_three_jwt_parts(client):
    resp = client.post("/api/auth/register", json=new_user())
    token = resp.json()["access_token"]
    assert len(token.split(".")) == 3


# ── Login ─────────────────────────────────────────────────────────────────────

def test_TC08_valid_login_returns_token(client):
    user = new_user()
    client.post("/api/auth/register", json=user)
    resp = client.post("/api/auth/login", json={
        "email": user["email"], "password": user["password"]
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_TC09_wrong_password_returns_401(client):
    user = new_user()
    client.post("/api/auth/register", json=user)
    resp = client.post("/api/auth/login", json={
        "email": user["email"], "password": "WrongPass999!"
    })
    assert resp.status_code == 401


def test_TC10_nonexistent_email_returns_401(client):
    resp = client.post("/api/auth/login", json={
        "email": "ghost_nobody@nowhere.com", "password": "Any123!"
    })
    assert resp.status_code == 401


def test_TC11_login_missing_password_returns_422(client):
    resp = client.post("/api/auth/login", json={"email": "a@b.com"})
    assert resp.status_code == 422


def test_TC12_disabled_account_returns_403(client):
    """
    Register a user via API, then disable them directly in the DB,
    using the same session the app uses (override_get_db) to avoid locking.
    """
    from app.models.models import User
    from app.models.database import get_db as _real_get_db

    user = new_user()
    resp = client.post("/api/auth/register", json=user)
    assert resp.status_code == 200
    user_id = resp.json()["user"]["id"]

    # Disable via the app's own DB session (avoids SQLite lock conflict)
    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        u.is_active = False
        db.commit()
    finally:
        db.close()

    resp2 = client.post("/api/auth/login", json={
        "email": user["email"], "password": user["password"]
    })
    assert resp2.status_code == 403


# import needed for TC12
from conftest import TestingSessionLocal
