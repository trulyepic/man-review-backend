from itsdangerous import URLSafeTimedSerializer
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")


SALT = "email-confirmation"

serializer = URLSafeTimedSerializer(SECRET_KEY)

def generate_email_token(email: str) -> str:
    return serializer.dumps(email, salt=SALT)

def verify_email_token(token: str, max_age: int = 3600) -> str:
    try:
        return serializer.loads(token, salt=SALT, max_age=max_age)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

