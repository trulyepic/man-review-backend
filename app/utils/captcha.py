import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

async def verify_captcha(captcha_token: str):
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
