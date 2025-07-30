from fastapi import (APIRouter, Depends, HTTPException,
                     status, Query, Body)
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.email_service import send_verification_email
from app.limiter import limiter
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserOut, SignupResponse, UserLogin
from sqlalchemy.future import select
from passlib.hash import bcrypt
from fastapi.responses import JSONResponse
from fastapi import Request

from app.utils.captcha import verify_captcha
from app.utils.token_utils import create_access_token
from app.utils.email_token_utils import verify_email_token, generate_email_token
from google.oauth2 import id_token
from google.auth.transport import requests
import os

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



@router.post("/signup", response_model=SignupResponse)
@limiter.limit("5/minute")
async def signup(_request: Request, user: UserCreate,
                    captcha_token: str = Body(...),
                 db: AsyncSession = Depends(get_db)):
    await verify_captcha(captcha_token)
    result = await db.execute(select(User).where(User.username == user.username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    hashed = bcrypt.hash(user.password)
    new_user = User(
        username=user.username,
        password=hashed,
        email=str(user.email),
        is_verified=False
    )

    try:
        db.add(new_user)
        await db.flush()  # Write to DB without committing yet
        token = generate_email_token(str(user.email))
        send_verification_email(str(user.email), token)
        await db.commit()  # Commit only if email sending succeeded
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Signup failed during email sending")

    print("CREATED USER:", new_user.username, new_user.is_verified)

    return SignupResponse(
        message="User created successfully. Please verify your email.",
        token=token
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

        email = id_info["email"]
        username = id_info.get("name", email.split("@")[0])  # fallback

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                username=username,
                password="",
                is_verified=True,
                role="GENERAL"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token(user)

        return {
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Google token")



@router.post("/login")
@limiter.limit("5/minute")
async def login(_request: Request, user: UserLogin, captcha_token: str = Body(...),
    db: AsyncSession = Depends(get_db)):

    await verify_captcha(captcha_token)
    # 🚨 Add this check to prevent empty input
    if not user.username.strip() or not user.password.strip():
        raise HTTPException(status_code=400, detail="Username and password are required")

    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalar_one_or_none()

    if not db_user or not bcrypt.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = create_access_token(db_user)

    return JSONResponse({
        "access_token": access_token,
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "role": db_user.role
        }
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