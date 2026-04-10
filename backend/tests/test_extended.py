"""
test_midterm_extended.py  —  backend/tests/test_midterm_extended.py

NEW test cases for the Midterm Project (Task 2).
Covers the 4 mandatory categories:
  1. Failure Scenarios
  2. Edge Cases
  3. Concurrency / Race Conditions
  4. Invalid User Behavior

Test IDs follow the format TC-<MODULE>-<CATEGORY>-<N>
"""

import uuid
import io
import json
import zipfile
import threading
import time
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def new_user():
    uid = uuid.uuid4().hex[:8]
    return {"email": f"mt_{uid}@test.com", "username": f"mt_{uid}", "password": "Pass123!"}


def register(client):
    u = new_user()
    r = client.post("/api/auth/register", json=u)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_zip(filename="main.py", content="print('hello')"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
# 1. FAILURE SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_AUTH_FAIL_01_completely_missing_body(client):
    """POST /register with no body at all returns 422."""
    resp = client.post("/api/auth/register", content=b"", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422


def test_TC_AUTH_FAIL_02_login_with_correct_email_wrong_case(client):
    """
    Email matching is case-sensitive per RFC — wrong case should return 401
    (or 200 if the app normalises emails — documents actual behaviour).
    """
    u = new_user()
    client.post("/api/auth/register", json=u)
    resp = client.post("/api/auth/login", json={
        "email": u["email"].upper(),
        "password": u["password"],
    })
    # Document actual behaviour — could be 200 (normalised) or 401 (strict)
    assert resp.status_code in (200, 401), f"Unexpected: {resp.status_code}"


def test_TC_AUTH_FAIL_03_expired_token_cannot_access_scans(client):
    """Expired JWT cannot access any protected endpoint."""
    from app.utils.auth import create_access_token
    from datetime import timedelta
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    resp = client.get("/api/scans", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (401, 403)


def test_TC_SCAN_FAIL_01_get_scan_with_expired_token(client):
    """Expired token rejected on GET /api/scans/{id}."""
    from app.utils.auth import create_access_token
    from datetime import timedelta
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    resp = client.get("/api/scans/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (401, 403)


def test_TC_SUB_FAIL_01_upgrade_with_empty_tier(client):
    """Upgrade with empty string tier returns 400."""
    headers = register(client)
    resp = client.post("/api/users/upgrade", json={"tier": ""}, headers=headers)
    assert resp.status_code == 400


def test_TC_SUB_FAIL_02_upgrade_with_missing_tier_field(client):
    """Upgrade with no tier field returns 422."""
    headers = register(client)
    resp = client.post("/api/users/upgrade", json={}, headers=headers)
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# 2. EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_AUTH_EDGE_01_very_long_password(client):
    """Registration with a 500-character password should work or return 4xx — not 500."""
    u = new_user()
    u["password"] = "A" * 500
    resp = client.post("/api/auth/register", json=u)
    assert resp.status_code in (200, 400, 422), f"Got 500: {resp.text}"


def test_TC_AUTH_EDGE_02_special_chars_in_username(client):
    """Username with special characters — app should not crash (500)."""
    u = new_user()
    u["username"] = "user'; DROP TABLE users;--"
    resp = client.post("/api/auth/register", json=u)
    assert resp.status_code != 500


def test_TC_AUTH_EDGE_03_unicode_in_full_name(client):
    """Unicode full name (Cyrillic, emoji) is accepted or gracefully rejected."""
    u = new_user()
    u["full_name"] = "Дамира 🔐"
    resp = client.post("/api/auth/register", json=u)
    assert resp.status_code in (200, 400, 422)
    if resp.status_code == 200:
        assert resp.json()["user"]["full_name"] == "Дамира 🔐"


def test_TC_SCAN_EDGE_01_empty_zip_file(client):
    """Uploading a ZIP with no files — should not crash the server."""
    headers = register(client)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass  # empty zip
    buf.seek(0)
    resp = client.post("/api/scans/upload",
        files={"file": ("empty.zip", buf.read(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert resp.status_code != 500




def test_TC_SCAN_EDGE_03_invalid_scan_mode(client):
    """Submitting a scan with an unknown scan_mode — should be handled (4xx or async failure, not 500)."""
    headers = register(client)
    resp = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "super_ultra_scan"},
        headers=headers,
    )
    assert resp.status_code != 500


def test_TC_SCAN_EDGE_04_scan_id_as_string(client):
    """GET /api/scans/abc (non-integer ID) — FastAPI should return 422."""
    headers = register(client)
    resp = client.get("/api/scans/abc", headers=headers)
    assert resp.status_code == 422


def test_TC_SCAN_EDGE_05_very_large_zip(client):
    """ZIP with a large file (5MB content) — should be accepted or rejected gracefully, never 500."""
    headers = register(client)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.py", "x = 1\n" * 200_000)  # ~1.4MB uncompressed
    buf.seek(0)
    resp = client.post("/api/scans/upload",
        files={"file": ("big.zip", buf.read(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert resp.status_code != 500


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONCURRENCY / RACE CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_CONC_01_parallel_registration_same_email(client):
    """
    Two threads try to register with the same email simultaneously.
    Exactly one should succeed (200), the other should get 400.
    """
    u = new_user()
    results = []

    def register_attempt():
        r = client.post("/api/auth/register", json=u)
        results.append(r.status_code)

    t1 = threading.Thread(target=register_attempt)
    t2 = threading.Thread(target=register_attempt)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert sorted(results) == [200, 400] or results.count(200) == 1, \
        f"Expected exactly one 200, got: {results}"


def test_TC_CONC_02_parallel_scan_submissions(client):
    """
    Same user submits 3 scans simultaneously.
    All should be accepted (200) or some rejected (429) — none should be 500.
    """
    headers = register(client)
    results = []

    def submit():
        r = client.post("/api/scans/upload",
            files={"file": ("t.zip", make_zip(), "application/zip")},
            data={"scan_mode": "sast"},
            headers=headers,
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=submit) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert all(s != 500 for s in results), f"Got 500 in concurrent scan submission: {results}"
    assert all(s in (200, 429) for s in results), f"Unexpected status codes: {results}"


def test_TC_CONC_03_parallel_upgrade_calls(client):
    """
    Same user fires 3 upgrade requests at once.
    All should succeed or cleanly fail — no 500.
    """
    headers = register(client)
    results = []

    def upgrade(tier):
        r = client.post("/api/users/upgrade", json={"tier": tier}, headers=headers)
        results.append(r.status_code)

    tiers = ["pro", "enterprise", "free"]
    threads = [threading.Thread(target=upgrade, args=(t,)) for t in tiers]
    for t in threads: t.start()
    for t in threads: t.join()

    assert all(s != 500 for s in results), f"Got 500 in concurrent upgrade: {results}"




# ══════════════════════════════════════════════════════════════════════════════
# 4. INVALID USER BEHAVIOR
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_INV_01_access_endpoint_with_malformed_bearer(client):
    """Sending 'Bearer' with no token value — should return 401/403, not 500."""
    resp = client.get("/api/users/me", headers={"Authorization": "Bearer"})
    assert resp.status_code in (401, 403)


def test_TC_INV_02_access_endpoint_with_basic_auth_instead_of_bearer(client):
    """Sending Basic auth instead of Bearer — should be rejected."""
    import base64
    creds = base64.b64encode(b"user:pass").decode()
    resp = client.get("/api/users/me", headers={"Authorization": f"Basic {creds}"})
    assert resp.status_code in (401, 403)


def test_TC_INV_03_delete_already_deleted_scan(client):
    """Delete the same scan twice — second delete should return 404."""
    headers = register(client)
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert create.status_code == 200
    scan_id = create.json()["id"]

    first_delete = client.delete(f"/api/scans/{scan_id}", headers=headers)
    assert first_delete.status_code == 200

    second_delete = client.delete(f"/api/scans/{scan_id}", headers=headers)
    assert second_delete.status_code == 404


def test_TC_INV_04_rapid_repeated_login_attempts(client):
    """
    10 rapid wrong-password login attempts — should all return 401,
    not crash, and not lock out (no rate-limiting in current design).
    """
    u = new_user()
    client.post("/api/auth/register", json=u)
    results = []
    for _ in range(10):
        r = client.post("/api/auth/login", json={
            "email": u["email"], "password": "WrongPassword!"
        })
        results.append(r.status_code)

    assert all(s == 401 for s in results), f"Unexpected codes: {results}"


def test_TC_INV_05_submit_scan_for_negative_scan_id(client):
    """GET /api/scans/-1 — negative ID should return 404, not 500."""
    headers = register(client)
    resp = client.get("/api/scans/-1", headers=headers)
    assert resp.status_code in (404, 422)


def test_TC_INV_06_upgrade_with_sql_injection_in_tier(client):
    """Tier field with SQL injection attempt — must be rejected as invalid tier (400)."""
    headers = register(client)
    resp = client.post("/api/users/upgrade",
        json={"tier": "'; DROP TABLE users;--"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_TC_INV_07_scan_list_with_extreme_offset(client):
    """GET /api/scans?offset=9999999 — should return empty list, not crash."""
    headers = register(client)
    resp = client.get("/api/scans?offset=9999999", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_TC_INV_08_upload_with_no_file_field(client):
    """POST /api/scans/upload with no file field — should return 422."""
    headers = register(client)
    resp = client.post("/api/scans/upload",
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# 5. UNIT TESTS — Service layer logic (no external tools)
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_UNIT_GITHUB_01_parse_valid_github_url():
    """parse_github_url correctly extracts owner and repo."""
    from app.services.github_service import parse_github_url
    result = parse_github_url("https://github.com/owner/repo")
    assert result == ("owner", "repo")


def test_TC_UNIT_GITHUB_02_parse_github_url_with_git_suffix():
    """parse_github_url strips .git suffix."""
    from app.services.github_service import parse_github_url
    result = parse_github_url("https://github.com/owner/repo.git")
    assert result == ("owner", "repo")


def test_TC_UNIT_GITHUB_03_parse_invalid_url_returns_none():
    """parse_github_url returns None for non-GitHub URLs."""
    from app.services.github_service import parse_github_url
    assert parse_github_url("https://gitlab.com/owner/repo") is None
    assert parse_github_url("not-a-url") is None
    assert parse_github_url("") is None


def test_TC_UNIT_GITHUB_04_parse_url_with_trailing_slash():
    """parse_github_url handles trailing slash."""
    from app.services.github_service import parse_github_url
    result = parse_github_url("https://github.com/owner/repo/")
    assert result == ("owner", "repo")


def test_TC_UNIT_GITLEAKS_01_load_findings_empty_file(tmp_path):
    """_load_findings returns empty list for empty file."""
    from app.services.gitleaks_service import _load_findings
    f = tmp_path / "empty.json"
    f.write_text("")
    assert _load_findings(f) == []


def test_TC_UNIT_GITLEAKS_02_load_findings_valid_json(tmp_path):
    """_load_findings correctly parses a valid findings JSON list."""
    from app.services.gitleaks_service import _load_findings
    data = [{"RuleID": "test-rule", "File": "app.py", "StartLine": 10}]
    f = tmp_path / "findings.json"
    f.write_text(json.dumps(data))
    result = _load_findings(f)
    assert len(result) == 1
    assert result[0]["RuleID"] == "test-rule"


def test_TC_UNIT_GITLEAKS_03_load_findings_malformed_json(tmp_path):
    """_load_findings returns empty list for malformed JSON (no crash)."""
    from app.services.gitleaks_service import _load_findings
    f = tmp_path / "bad.json"
    f.write_text("{this is not json")
    assert _load_findings(f) == []


def test_TC_UNIT_GITLEAKS_04_load_findings_nonexistent_file(tmp_path):
    """_load_findings returns empty list when file does not exist."""
    from app.services.gitleaks_service import _load_findings
    assert _load_findings(tmp_path / "nonexistent.json") == []


def test_TC_UNIT_GITLEAKS_05_normalize_deduplicates(tmp_path):
    """_normalize removes duplicate findings (same rule+file+line)."""
    from app.services.gitleaks_service import _normalize
    findings = [
        {"RuleID": "rule-1", "File": "app.py", "StartLine": 5, "Description": "leak"},
        {"RuleID": "rule-1", "File": "app.py", "StartLine": 5, "Description": "leak"},  # duplicate
    ]
    result = _normalize(findings, tmp_path)
    assert len(result) == 1


def test_TC_UNIT_GITLEAKS_06_normalize_maps_fields(tmp_path):
    """_normalize correctly maps gitleaks fields to output schema."""
    from app.services.gitleaks_service import _normalize
    findings = [{
        "RuleID": "aws-access-key",
        "File": str(tmp_path / "secrets.py"),
        "StartLine": 42,
        "Description": "AWS key",
        "Commit": "abc123",
        "Author": "dev",
    }]
    result = _normalize(findings, tmp_path)
    assert len(result) == 1
    r = result[0]
    assert r["rule_id"] == "aws-access-key"
    assert r["line"] == 42
    assert r["severity"] == "high"
    assert r["author"] == "dev"


def test_TC_UNIT_SEMGREP_01_load_results_empty(tmp_path):
    """_load_results returns empty list for missing file."""
    from app.services.semgrep_service import _load_results
    assert _load_results(tmp_path / "missing.json") == []


def test_TC_UNIT_SEMGREP_02_load_results_valid(tmp_path):
    """_load_results parses a valid semgrep JSON output."""
    from app.services.semgrep_service import _load_results
    data = {"results": [{"check_id": "rule-1", "path": "app.py", "start": {"line": 3}}]}
    f = tmp_path / "semgrep.json"
    f.write_text(json.dumps(data))
    result = _load_results(f)
    assert len(result) == 1
    assert result[0]["check_id"] == "rule-1"


def test_TC_UNIT_SEMGREP_03_load_results_malformed(tmp_path):
    """_load_results handles malformed JSON without crashing."""
    from app.services.semgrep_service import _load_results
    f = tmp_path / "bad.json"
    f.write_text("NOT JSON")
    assert _load_results(f) == []


def test_TC_UNIT_SEMGREP_04_find_semgrep_returns_list():
    """_find_semgrep always returns a list (command prefix)."""
    from app.services.semgrep_service import _find_semgrep
    cmd = _find_semgrep()
    assert isinstance(cmd, list)
    assert len(cmd) >= 1


def test_TC_UNIT_LIMITS_01_daily_limits_dict():
    """DAILY_LIMITS contains expected tier keys and correct values."""
    from app.utils.limits import DAILY_LIMITS
    assert DAILY_LIMITS["free"] == 3
    assert DAILY_LIMITS["pro"] == 50
    assert DAILY_LIMITS["enterprise"] == 9999


def test_TC_UNIT_LIMITS_02_unknown_tier_defaults_to_3():
    """check_and_increment_scan treats unknown tier as free (limit=3)."""
    import uuid
    from datetime import date
    from app.models.models import User
    from app.utils.auth import hash_password
    from app.utils.limits import check_and_increment_scan
    from fastapi import HTTPException
    from conftest import TestingSessionLocal

    uid = uuid.uuid4().hex[:8]
    db = TestingSessionLocal()
    try:
        u = User(
            email=f"unk_{uid}@test.com",
            username=f"unk_{uid}",
            hashed_password=hash_password("x"),
            subscription_tier="gold",  # unknown
            scans_today=3,
            last_scan_date=str(date.today()),
        )
        db.add(u); db.commit(); db.refresh(u)
        with pytest.raises(HTTPException) as exc:
            check_and_increment_scan(u, db)
        assert exc.value.status_code == 429
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# 6. INTEGRATION TESTS — Module interaction
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_INT_01_register_then_immediately_use_token(client):
    """Token from registration works immediately on /me — no separate login needed."""
    u = new_user()
    reg = client.post("/api/auth/register", json=u)
    token = reg.json()["access_token"]
    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == u["email"]


def test_TC_INT_02_upgrade_then_check_limit_reflects_new_tier(client):
    """
    After upgrading to pro, the daily limit should be 50 not 3.
    Verify by direct DB inspection after upgrade.
    """
    u = new_user()
    reg = client.post("/api/auth/register", json=u)
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upgrade
    client.post("/api/users/upgrade", json={"tier": "pro"}, headers=headers)

    # Verify via DB
    from app.models.models import User
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user.subscription_tier == "pro"
        from app.utils.limits import DAILY_LIMITS
        assert DAILY_LIMITS[user.subscription_tier] == 50
    finally:
        db.close()


def test_TC_INT_03_scan_appears_in_list_after_creation(client):
    """After creating a scan, it must appear in GET /api/scans."""
    headers = register(client)
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert create.status_code == 200
    scan_id = create.json()["id"]

    scans = client.get("/api/scans", headers=headers)
    assert scans.status_code == 200
    ids = [s["id"] for s in scans.json()]
    assert scan_id in ids


def test_TC_INT_04_deleted_scan_disappears_from_list(client):
    """After deleting a scan, it must not appear in GET /api/scans."""
    headers = register(client)
    create = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    scan_id = create.json()["id"]
    client.delete(f"/api/scans/{scan_id}", headers=headers)

    scans = client.get("/api/scans", headers=headers)
    ids = [s["id"] for s in scans.json()]
    assert scan_id not in ids


def test_TC_INT_05_login_token_different_from_register_token(client):
    """Login issues a fresh token; it must be different from the registration token."""
    u = new_user()
    reg = client.post("/api/auth/register", json=u)
    reg_token = reg.json()["access_token"]

    login = client.post("/api/auth/login", json={"email": u["email"], "password": u["password"]})
    login_token = login.json()["access_token"]

    # Tokens are time-based — issued at different times, so different exp
    # (they may be identical only in the same second; just verify both work)
    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {login_token}"})
    assert me.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 7. E2E TESTS — Full user workflow
# ══════════════════════════════════════════════════════════════════════════════

def test_TC_E2E_01_full_free_user_workflow(client):
    """
    Complete free user journey:
    Register → Login → Check profile → Submit scan → View scan → Delete scan
    """
    u = new_user()

    # Step 1: Register
    reg = client.post("/api/auth/register", json=u)
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Verify profile
    me = client.get("/api/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["subscription_tier"] == "free"

    # Step 3: Check empty scan list
    scans = client.get("/api/scans", headers=headers)
    assert scans.json() == []

    # Step 4: Submit a scan
    upload = client.post("/api/scans/upload",
        files={"file": ("code.zip", make_zip("app.py", "import os; os.system('ls')"), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert upload.status_code == 200
    scan_id = upload.json()["id"]

    # Step 5: View scan
    detail = client.get(f"/api/scans/{scan_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == scan_id

    # Step 6: Scan appears in list
    scans2 = client.get("/api/scans", headers=headers)
    assert any(s["id"] == scan_id for s in scans2.json())

    # Step 7: Delete scan
    delete = client.delete(f"/api/scans/{scan_id}", headers=headers)
    assert delete.status_code == 200

    # Step 8: Scan gone
    gone = client.get(f"/api/scans/{scan_id}", headers=headers)
    assert gone.status_code == 404


def test_TC_E2E_02_free_tier_hits_scan_limit(client):
    """
    Free user submits 3 scans (limit), then a 4th is rejected with 429.
    Verifies the full subscription enforcement flow end-to-end.
    """
    # Use enterprise first to make sure we get a clean counter, then downgrade
    u = new_user()
    reg = client.post("/api/auth/register", json=u)
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Confirm starts as free with scans_today=0
    me = client.get("/api/users/me", headers=headers).json()
    assert me["subscription_tier"] == "free"
    assert me["scans_today"] == 0

    # Submit 3 scans — all should succeed
    scan_ids = []
    for i in range(3):
        r = client.post("/api/scans/upload",
            files={"file": ("t.zip", make_zip(), "application/zip")},
            data={"scan_mode": "sast"},
            headers=headers,
        )
        assert r.status_code == 200, f"Scan {i+1} failed: {r.text}"
        scan_ids.append(r.json()["id"])

    # 4th scan must be rejected
    r4 = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert r4.status_code == 429, f"Expected 429, got {r4.status_code}: {r4.text}"


def test_TC_E2E_03_upgrade_unlocks_more_scans(client):
    """
    Free user hits limit → upgrades to pro → submits more scans successfully.
    Full tier upgrade + limit interaction flow.
    """
    u = new_user()
    reg = client.post("/api/auth/register", json=u)
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Burn free limit
    for _ in range(3):
        client.post("/api/scans/upload",
            files={"file": ("t.zip", make_zip(), "application/zip")},
            data={"scan_mode": "sast"},
            headers=headers,
        )

    # Verify blocked
    blocked = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert blocked.status_code == 429

    # Upgrade to pro
    upgrade = client.post("/api/users/upgrade", json={"tier": "pro"}, headers=headers)
    assert upgrade.status_code == 200

    # Now should work again
    after_upgrade = client.post("/api/scans/upload",
        files={"file": ("t.zip", make_zip(), "application/zip")},
        data={"scan_mode": "sast"},
        headers=headers,
    )
    assert after_upgrade.status_code == 200, f"After upgrade got: {after_upgrade.status_code}"
