from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from jose import jwt

from app.utils import token_utils


def test_create_access_token_includes_expected_user_claims(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    user = SimpleNamespace(id=42, username="toonfan", role="admin")

    token = token_utils.create_access_token(user)
    payload = jwt.decode(token, "test-secret-key-with-at-least-32-characters", algorithms=["HS256"])

    assert payload["id"] == 42
    assert payload["sub"] == "toonfan"
    assert payload["role"] == "admin"
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(timezone.utc)


def test_create_access_token_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    user = SimpleNamespace(id=42, username="toonfan", role="user")

    with pytest.raises(RuntimeError, match="SECRET_KEY is not configured"):
        token_utils.create_access_token(user)


def test_create_access_token_rejects_short_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "too-short")
    user = SimpleNamespace(id=42, username="toonfan", role="user")

    with pytest.raises(RuntimeError, match="SECRET_KEY is too short"):
        token_utils.create_access_token(user)
