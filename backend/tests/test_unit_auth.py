"""
test_unit_auth.py — Unit tests for auth utility functions.

Covers:
  TC31  hash_password produces a non-plaintext hash
  TC32  verify_password returns True for correct password
  TC33  verify_password returns False for wrong password
  TC34  create_access_token returns a valid JWT with expected sub
  TC35  Expired token is rejected by get_current_user
  TC36  Token with wrong secret is rejected
  TC37  Token with tampered payload is rejected
"""

import uuid
import time
import pytest
from datetime import timedelta


def test_TC31_hash_password_is_not_plaintext():
    from app.utils.auth import hash_password
    plain = "MySuperSecret123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert len(hashed) > 20  # bcrypt hash is ~60 chars


def test_TC32_verify_password_correct():
    from app.utils.auth import hash_password, verify_password
    plain = "CorrectPassword!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_TC33_verify_password_wrong():
    from app.utils.auth import hash_password, verify_password
    hashed = hash_password("RightPassword")
    assert verify_password("WrongPassword", hashed) is False


def test_TC34_create_access_token_has_sub():
    from app.utils.auth import create_access_token
    from jose import jwt
    import os

    SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = os.environ["ALGORITHM"]

    token = create_access_token({"sub": "42"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_TC35_expired_token_is_rejected(client):
    from app.utils.auth import create_access_token
    # Create a token that expired 1 second ago
    token = create_access_token({"sub": "999"}, expires_delta=timedelta(seconds=-1))
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (401, 403)


def test_TC36_token_with_wrong_secret_is_rejected(client):
    from jose import jwt
    import os
    fake_token = jwt.encode(
        {"sub": "1", "exp": int(time.time()) + 3600},
        "completely-wrong-secret-key",
        algorithm="HS256",
    )
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert resp.status_code in (401, 403)


def test_TC37_tampered_token_is_rejected(client, registered_user):
    token = registered_user["token"]
    # Tamper: change last character
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code in (401, 403)
