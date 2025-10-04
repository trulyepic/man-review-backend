from fastapi import (APIRouter, Depends, HTTPException,
                     status, Query, Body)
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.email_service import send_verification_email
from app.limiter import limiter
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserOut, SignupResponse, UserLogin, ResendVerification
from sqlalchemy.future import select
from passlib.hash import bcrypt
from fastapi.responses import JSONResponse
from fastapi import Request

from app.utils.captcha import verify_captcha
from app.utils.token_utils import create_access_token
from app.utils.email_token_utils import verify_email_token, generate_email_token
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, timezone
import os
from jose import JWTError

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



@router.post("/signup", response_model=SignupResponse)
@limiter.limit("5/minute")
async def signup(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    await verify_captcha(user.captcha_token)

    username_norm = user.username.strip()
    email_norm = str(user.email).strip().lower()

    # Check username OR email conflict in a single round-trip
    result = await db.execute(
        select(User).where(
            (User.username == username_norm) | (func.lower(User.email) == email_norm)
        )
    )
    existing = result.scalars().all()

    if any((u.email or "").strip().lower() == email_norm for u in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    if any(u.username == username_norm for u in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    hashed = bcrypt.hash(user.password)
    new_user = User(
        username=username_norm,
        password=hashed,
        email=email_norm,           # store normalized email
        is_verified=False,
        registered_at=datetime.now(timezone.utc),
    )

    try:
        db.add(new_user)
        await db.flush()  # Write to DB without committing yet
        token = generate_email_token(email_norm)
        send_verification_email(email_norm, token)
        await db.commit()  # Commit only if email sending succeeded
        await db.refresh(new_user)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Signup failed during email sending")

    return SignupResponse(
        message="User created successfully. Please verify your email.",
        token=token,
    )


# @router.post("/signup", response_model=SignupResponse)
# async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     # 🔍 Check if the username already exists
#     result = await db.execute(select(User).where(User.username == user.username))
#     existing_user = result.scalar_one_or_none()
#
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="Username already exists"
#         )
#
#     # ✅ Create user
#     hashed = bcrypt.hash(user.password)
#     new_user = User(
#         username=user.username,
#         password=hashed,
#         email=str(user.email),
#         is_verified=False
#     )
#     db.add(new_user)
#     await db.commit()
#     await db.refresh(new_user)
#
#     token = generate_email_token(str(user.email))
#     send_verification_email(str(user.email), token)
#     # return new_user
#     return SignupResponse(
#         message="User created successfully. Please verify your email.",
#         token=token
#     )


@router.post("/google-oauth")
async def google_oauth(payload: dict, db: AsyncSession = Depends(get_db)):
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), os.getenv("GOOGLE_CLIENT_ID"))

        email = id_info["email"].strip().lower()
        username = id_info.get("name", email.split("@")[0]).strip()

        result = await db.execute(
            select(User).where(func.lower(User.email) == email)
        )
        user = result.scalars().first()

        if not user:
            user = User(
                email=email,
                username=username,
                password="",
                is_verified=True,
                role="GENERAL",
                registered_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token(user)

        return {
            "access_token": access_token,
            "user": {"id": user.id, "username": user.username, "role": user.role},
        }

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")




@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, user: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        await verify_captcha(user.captcha_token)
    except HTTPException as he:
        # Keep this: shows exact captcha failure reason from verify_captcha
        print(f"[LOGIN] Captcha verification failed -> {he.detail}")
        raise
    except Exception as e:
        print(f"[LOGIN] Unexpected captcha error -> {e}")
        raise HTTPException(status_code=500, detail=f"CAPTCHA verification error: {e}")

    if not user.username.strip() or not user.password.strip():
        raise HTTPException(status_code=400, detail="Username and password are required")

    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalar_one_or_none()

    if not db_user or not bcrypt.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    try:
        access_token = create_access_token(db_user)
    except Exception as e:
        print(f"[LOGIN] Token creation failed -> {e}")
        raise HTTPException(status_code=500, detail=f"Token creation failed: {e}")

    return JSONResponse({
        "access_token": access_token,
        "user": {"id": db_user.id, "username": db_user.username, "role": db_user.role}
    })



# @router.post("/login")
# async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.username == user.username))
#     db_user = result.scalar_one_or_none()
#
#     if not db_user or not bcrypt.verify(user.password, db_user.password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
#
#     if not db_user.is_verified:
#         raise HTTPException(status_code=403, detail="Email not verified")
#
#     # ✅ Create JWT
#     # token_data = {"sub": db_user.username, "role": db_user.role, "id": db_user.id,}
#     # access_token = create_access_token(data=token_data)
#     access_token = create_access_token(db_user)
#
#     return JSONResponse({
#         "access_token": access_token,
#         "user": {
#             "id": db_user.id,
#             "username": db_user.username,
#             "role": db_user.role
#         }
#     })


@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    email = verify_email_token(token)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "Email already verified"}

    user.is_verified = True
    await db.commit()

    return {"message": "Email verification successful"}



@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    payload: ResendVerification,
    db: AsyncSession = Depends(get_db),
):
    # (Optional) require CAPTCHA; flip this on if you get abuse
    if payload.captcha_token:
        try:
            await verify_captcha(payload.captcha_token)
        except Exception:
            # Don’t reveal granularity; generic message prevents probing
            return {"message": "If an account exists, a new verification link has been sent."}

    if not payload.email and not payload.username:
        raise HTTPException(status_code=400, detail="Provide email or username")

    # Lookup by email first (if provided), else username
    user = None
    if payload.email:
        result = await db.execute(select(User).where(User.email == str(payload.email)))
        user = result.scalar_one_or_none()
    if not user and payload.username:
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()

    # Always return a generic message to avoid user-enumeration
    if not user:
        return {"message": "If an account exists, a new verification link has been sent."}

    if user.is_verified:
        return {"message": "Email is already verified. You can log in."}

    try:
        token = generate_email_token(str(user.email))
        send_verification_email(str(user.email), token)
    except Exception:
        # Don’t leak details; stay generic
        return {"message": "If an account exists, a new verification link has been sent."}

    return {"message": "Verification email sent. Please check your inbox."}