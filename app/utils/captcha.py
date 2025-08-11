import os
import httpx
from fastapi import HTTPException

async def verify_captcha(captcha_token: str):
    secret = os.getenv("RECAPTCHA_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="Captcha secret key not configured")

    async with httpx.AsyncClient() as client:
        res = await client.post(
             "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": captcha_token},
        )
        data = res.json()
        if not data.get("success"):
            raise HTTPException(status_code=400, detail="Captcha verification failed")