import pytest
from fastapi import HTTPException

from app.utils import captcha

pytestmark = pytest.mark.anyio


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, *args, payload=None, error=None, **kwargs):
        self.payload = payload or {"success": True}
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        if self.error:
            raise self.error
        return FakeResponse(self.payload)


def test_truthy_detects_enabled_values():
    assert captcha._truthy("true") is True
    assert captcha._truthy("1") is True
    assert captcha._truthy("yes") is True
    assert captcha._truthy("off") is False


async def test_verify_captcha_legacy_accepts_success_response(monkeypatch):
    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(captcha.httpx, "AsyncClient", lambda *args, **kwargs: FakeAsyncClient())

    assert await captcha._verify_captcha_legacy("captcha-token") is None


async def test_verify_captcha_legacy_requires_secret_key(monkeypatch):
    monkeypatch.delenv("RECAPTCHA_SECRET_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await captcha._verify_captcha_legacy("captcha-token")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Captcha secret key not configured"


async def test_verify_captcha_legacy_rejects_failed_response(monkeypatch):
    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(
        captcha.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(
            payload={"success": False, "error-codes": ["invalid-input-response"]}
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await captcha._verify_captcha_legacy("captcha-token")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Captcha verification failed (invalid-input-response)"


async def test_verify_captcha_legacy_wraps_network_errors(monkeypatch):
    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(
        captcha.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(error=RuntimeError("network down")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await captcha._verify_captcha_legacy("captcha-token")

    assert exc_info.value.status_code == 502
    assert "Captcha verification request failed" in exc_info.value.detail
