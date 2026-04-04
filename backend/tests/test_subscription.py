"""
test_subscription.py — Tests for subscription tiers and daily scan limits.

Covers:
  TC38  Free user defaults to 3 scans/day limit
  TC39  Pro user has 50 scans/day limit
  TC40  Enterprise user has effectively unlimited scans
  TC41  Downgrade from pro back to free works
  TC42  scans_today increments correctly after each allowed scan
  TC43  Invalid tier in upgrade payload → 400
"""

import uuid
import pytest
from datetime import date
from fastapi import HTTPException


def make_user(db, tier="free", scans_today=0, last_scan_date=None):
    from app.models.models import User
    from app.utils.auth import hash_password

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"sub_{uid}@test.com",
        username=f"sub_{uid}",
        hashed_password=hash_password("Pass!"),
        subscription_tier=tier,
        scans_today=scans_today,
        last_scan_date=last_scan_date or str(date.today()),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# TC38 — Free tier allows exactly 3 scans, then blocks
# ─────────────────────────────────────────────────────────────────────────────
def test_TC38_free_tier_limit_is_3(db):
    from app.utils.limits import check_and_increment_scan
    user = make_user(db, tier="free", scans_today=0)

    for _ in range(3):
        check_and_increment_scan(user, db)

    assert user.scans_today == 3

    with pytest.raises(HTTPException) as exc:
        check_and_increment_scan(user, db)
    assert exc.value.status_code == 429


# ─────────────────────────────────────────────────────────────────────────────
# TC39 — Pro tier limit is 50
# ─────────────────────────────────────────────────────────────────────────────
def test_TC39_pro_tier_limit_is_50(db):
    from app.utils.limits import check_and_increment_scan
    user = make_user(db, tier="pro", scans_today=49)

    check_and_increment_scan(user, db)  # 50th scan — OK
    assert user.scans_today == 50

    with pytest.raises(HTTPException) as exc:
        check_and_increment_scan(user, db)  # 51st — blocked
    assert exc.value.status_code == 429


# ─────────────────────────────────────────────────────────────────────────────
# TC40 — Enterprise tier is effectively unlimited (9999)
# ─────────────────────────────────────────────────────────────────────────────
def test_TC40_enterprise_tier_high_limit(db):
    from app.utils.limits import check_and_increment_scan
    user = make_user(db, tier="enterprise", scans_today=500)

    # Should not raise at scan 501
    check_and_increment_scan(user, db)
    assert user.scans_today == 501


# ─────────────────────────────────────────────────────────────────────────────
# TC41 — Downgrade from pro back to free via API
# ─────────────────────────────────────────────────────────────────────────────
def test_TC41_downgrade_to_free(client):
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/auth/register", json={
        "email": f"downgrade_{uid}@test.com",
        "username": f"downgrade_{uid}",
        "password": "Pass123!",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/users/upgrade", json={"tier": "pro"}, headers=headers)
    resp = client.post("/api/users/upgrade", json={"tier": "free"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["subscription_tier"] == "free"


# ─────────────────────────────────────────────────────────────────────────────
# TC42 — scans_today increments correctly
# ─────────────────────────────────────────────────────────────────────────────
def test_TC42_scans_today_increments(db):
    from app.utils.limits import check_and_increment_scan
    user = make_user(db, tier="pro", scans_today=0)

    check_and_increment_scan(user, db)
    assert user.scans_today == 1

    check_and_increment_scan(user, db)
    assert user.scans_today == 2


# ─────────────────────────────────────────────────────────────────────────────
# TC43 — Invalid tier via API → 400
# ─────────────────────────────────────────────────────────────────────────────
def test_TC43_invalid_tier_via_api_returns_400(client, auth_headers):
    resp = client.post("/api/users/upgrade", json={"tier": "platinum"}, headers=auth_headers)
    assert resp.status_code == 400
