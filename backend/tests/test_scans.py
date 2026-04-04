"""
test_scans.py  —  backend/tests/test_scans.py
Tests for GET/DELETE /api/scans and scan submission endpoints.
"""

import uuid
import io
import zipfile
import pytest
from conftest import TestingSessionLocal


def register_fresh(client):
    uid = uuid.uuid4().hex[:8]
    resp = client.post("/api/auth/register", json={
        "email":    f"scan_{uid}@test.com",
        "username": f"scan_{uid}",
        "password": "Pass123!",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("main.py", "print('hello')")
    buf.seek(0)
    return buf.read()


# ── List scans ────────────────────────────────────────────────────────────────

def test_TC22_list_scans_no_token_returns_403(client):
    resp = client.get("/api/scans")
    assert resp.status_code in (401, 403)


def test_TC23_list_scans_valid_token_returns_list(client, auth_headers):
    resp = client.get("/api/scans", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_TC24_new_user_has_empty_scan_list(client):
    headers = register_fresh(client)
    resp = client.get("/api/scans", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── Submit GitHub scan ────────────────────────────────────────────────────────

def test_TC25_github_scan_no_token_returns_403(client):
    resp = client.post("/api/scans/github", data={
        "repo_url": "https://github.com/owner/repo",
        "scan_mode": "secrets",
    })
    assert resp.status_code in (401, 403)


def test_TC26_github_scan_does_not_crash(client, auth_headers):
    """Invalid URL is accepted async or rejected — either way, no 500."""
    resp = client.post("/api/scans/github", data={
        "repo_url": "not-a-url",
        "scan_mode": "secrets",
    }, headers=auth_headers)
    assert resp.status_code != 500


# ── Submit ZIP scan ───────────────────────────────────────────────────────────

def test_TC27_zip_scan_no_token_returns_403(client):
    resp = client.post("/api/scans/upload",
        files={"file": ("test.zip", make_zip_bytes(), "application/zip")},
        data={"scan_mode": "sast"},
    )
    assert resp.status_code in (401, 403)


def test_TC28_zip_scan_valid_token_creates_scan(client, auth_headers):
    resp = client.post("/api/scans/upload",
        files={"file": ("test.zip", make_zip_bytes(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] in ("pending", "running", "completed", "failed")


# ── Get / delete individual scan ──────────────────────────────────────────────

def test_TC29_get_nonexistent_scan_returns_404(client, auth_headers):
    resp = client.get("/api/scans/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_TC30_get_own_scan_returns_200(client, auth_headers):
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip_bytes(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=auth_headers,
    )
    assert create.status_code == 200
    scan_id = create.json()["id"]
    resp = client.get(f"/api/scans/{scan_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


def test_TC31_cannot_access_other_users_scan(client):
    """User B registers via API, creates a scan, User A cannot see it."""
    headers_a = register_fresh(client)
    headers_b = register_fresh(client)

    # User A creates a scan
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip_bytes(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers_a,
    )
    assert create.status_code == 200
    scan_id = create.json()["id"]

    # User B tries to read it — must get 404, not the scan data
    resp = client.get(f"/api/scans/{scan_id}", headers=headers_b)
    assert resp.status_code == 404


def test_TC32_delete_own_scan_returns_200(client):
    # Fresh user avoids scan limit exhausted by earlier tests in this module
    headers = register_fresh(client)
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip_bytes(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert create.status_code == 200, f"Scan creation failed: {create.text}"
    scan_id = create.json()["id"]
    resp = client.delete(f"/api/scans/{scan_id}", headers=headers)
    assert resp.status_code == 200
    assert client.get(f"/api/scans/{scan_id}", headers=headers).status_code == 404


def test_TC33_delete_nonexistent_scan_returns_404(client, auth_headers):
    resp = client.delete("/api/scans/999999", headers=auth_headers)
    assert resp.status_code == 404


# ── Scan limit unit tests (no db fixture — uses app's own session) ─────────────

def test_TC34_free_tier_scan_limit_enforced():
    from datetime import date
    from app.models.models import User
    from app.utils.auth import hash_password
    from app.utils.limits import check_and_increment_scan
    from fastapi import HTTPException

    uid = uuid.uuid4().hex[:8]
    db = TestingSessionLocal()
    try:
        u = User(
            email=f"lim_{uid}@test.com",
            username=f"lim_{uid}",
            hashed_password=hash_password("x"),
            subscription_tier="free",
            scans_today=3,
            last_scan_date=str(date.today()),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        with pytest.raises(HTTPException) as exc:
            check_and_increment_scan(u, db)
        assert exc.value.status_code == 429
    finally:
        db.close()


def test_TC35_scan_counter_resets_on_new_day():
    from datetime import date
    from app.models.models import User
    from app.utils.auth import hash_password
    from app.utils.limits import check_and_increment_scan

    uid = uuid.uuid4().hex[:8]
    db = TestingSessionLocal()
    try:
        u = User(
            email=f"rst_{uid}@test.com",
            username=f"rst_{uid}",
            hashed_password=hash_password("x"),
            subscription_tier="free",
            scans_today=3,
            last_scan_date="2000-01-01",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        check_and_increment_scan(u, db)  # must not raise
        assert u.scans_today == 1
        assert u.last_scan_date == str(date.today())
    finally:
        db.close()
