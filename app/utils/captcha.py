from __future__ import annotations

import os
import httpx
import google.auth
from dotenv import load_dotenv
from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleAuthRequest

load_dotenv()

def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _enterprise_enabled() -> bool:
    return _truthy(os.getenv("RECAPTCHA_ENTERPRISE_ENABLED"))


async def _verify_captcha_enterprise(captcha_token: str, request=None):
    site_key = os.getenv("RECAPTCHA_SITE_KEY")
    project_id = os.getenv("RECAPTCHA_PROJECT_ID")

    if not site_key or not project_id:
        raise HTTPException(
            status_code=500,
            detail="reCAPTCHA Enterprise is enabled but RECAPTCHA_SITE_KEY or RECAPTCHA_PROJECT_ID is missing",
        )

    try:
        credentials, discovered_project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        if not project_id and discovered_project_id:
            project_id = discovered_project_id
        credentials.refresh(GoogleAuthRequest())
        access_token = credentials.token
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Google Cloud credentials for reCAPTCHA Enterprise: {e}",
        )

    if not access_token or not project_id:
        raise HTTPException(
            status_code=500,
            detail="reCAPTCHA Enterprise credentials are missing an access token or project ID",
        )

    user_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    event = {
        "token": (captcha_token or "").strip(),
        "siteKey": site_key,
    }
    if user_ip:
        event["userIpAddress"] = user_ip
    if user_agent:
        event["userAgent"] = user_agent

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.post(
                f"https://recaptchaenterprise.googleapis.com/v1/projects/{project_id}/assessments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"event": event},
            )
        data = res.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Captcha assessment request failed: {e}",
        )

    token_props = data.get("tokenProperties") or {}
    if not token_props.get("valid"):
        invalid_reason = token_props.get("invalidReason", "UNKNOWN")
        raise HTTPException(
            status_code=400,
            detail=f"Captcha verification failed ({invalid_reason})",
        )


async def _verify_captcha_legacy(captcha_token: str):
    secret = os.getenv("RECAPTCHA_SECRET_KEY")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Captcha secret key not configured"
        )

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret, "response": (captcha_token or "").strip()},
            )
        data = res.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Captcha verification request failed: {e}"
        )

    if not data.get("success"):
        codes = ", ".join(data.get("error-codes", []))
        raise HTTPException(
            status_code=400,
            detail=f"Captcha verification failed ({codes})"
        )

    # Optional hostname check:
    # allowed = os.getenv("RECAPTCHA_ALLOWED_HOSTNAMES")
    # if allowed:
    #     allowed_set = {h.strip().lower() for h in allowed.split(",") if h.strip()}
    #     host = (data.get("hostname") or "").lower()
    #     if host and allowed_set and host not in allowed_set:
    #         raise HTTPException(status_code=400, detail=f"Captcha hostname mismatch: {host}")


async def verify_captcha(captcha_token: str, request=None):
    if _enterprise_enabled():
        return await _verify_captcha_enterprise(captcha_token, request=request)
    return await _verify_captcha_legacy(captcha_token)
