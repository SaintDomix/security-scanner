"""
test_users.py — Automated tests for /api/users endpoints.

Covers:
  TC13  GET /api/users/me with valid token → 200 + user object
  TC14  GET /api/users/me without token → 403
  TC15  GET /api/users/me with invalid token → 403
  TC16  POST /api/users/upgrade to 'pro' → 200 + updated tier
  TC17  POST /api/users/upgrade to 'enterprise' → 200
  TC18  POST /api/users/upgrade to invalid tier → 400
  TC19  POST /api/users/upgrade without token → 403
  TC20  Upgrade persists — subsequent /me returns updated tier
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# TC13 — GET /api/users/me with valid token → 200
# ─────────────────────────────────────────────────────────────────────────────
def test_TC13_get_me_with_valid_token(client, registered_user, auth_headers):
    resp = client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == registered_user["email"]
    assert data["username"] == registered_user["username"]


# ─────────────────────────────────────────────────────────────────────────────
# TC14 — GET /api/users/me without token → 403
# ─────────────────────────────────────────────────────────────────────────────
def test_TC14_get_me_without_token_returns_403(client):
    resp = client.get("/api/users/me")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# TC15 — GET /api/users/me with garbage token → 403
# ─────────────────────────────────────────────────────────────────────────────
def test_TC15_get_me_with_invalid_token_returns_403(client):
    resp = client.get("/api/users/me", headers={"Authorization": "Bearer this.is.garbage"})
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# TC16 — Upgrade to 'pro' → 200 + tier updated
# ─────────────────────────────────────────────────────────────────────────────
def test_TC16_upgrade_to_pro(client, auth_headers):
    resp = client.post("/api/users/upgrade", json={"tier": "pro"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["subscription_tier"] == "pro"


# ─────────────────────────────────────────────────────────────────────────────
# TC17 — Upgrade to 'enterprise' → 200
# ─────────────────────────────────────────────────────────────────────────────
def test_TC17_upgrade_to_enterprise(client, auth_headers):
    resp = client.post("/api/users/upgrade", json={"tier": "enterprise"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["subscription_tier"] == "enterprise"


# ─────────────────────────────────────────────────────────────────────────────
# TC18 — Upgrade to invalid tier → 400
# ─────────────────────────────────────────────────────────────────────────────
def test_TC18_upgrade_to_invalid_tier_returns_400(client, auth_headers):
    resp = client.post("/api/users/upgrade", json={"tier": "super_ultra"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "invalid tier" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# TC19 — Upgrade without token → 403
# ─────────────────────────────────────────────────────────────────────────────
def test_TC19_upgrade_without_token_returns_403(client):
    resp = client.post("/api/users/upgrade", json={"tier": "pro"})
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# TC20 — Upgrade persists across subsequent /me calls
# ─────────────────────────────────────────────────────────────────────────────
def test_TC20_upgrade_persists(client, auth_headers):
    # Reset to free first
    client.post("/api/users/upgrade", json={"tier": "free"}, headers=auth_headers)

    # Upgrade to pro
    client.post("/api/users/upgrade", json={"tier": "pro"}, headers=auth_headers)

    # Verify via /me
    resp = client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["subscription_tier"] == "pro"
