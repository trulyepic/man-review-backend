from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserOut
from sqlalchemy.future import select
from passlib.hash import bcrypt
from fastapi.responses import JSONResponse
from app.utils.token_utils import create_access_token


router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/signup", response_model=UserOut)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # 🔍 Check if the username already exists
    result = await db.execute(select(User).where(User.username == user.username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    # ✅ Create user
    hashed = bcrypt.hash(user.password)
    new_user = User(username=user.username, password=hashed)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login")
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalar_one_or_none()

    if not db_user or not bcrypt.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ Create JWT
    # token_data = {"sub": db_user.username, "role": db_user.role, "id": db_user.id,}
    # access_token = create_access_token(data=token_data)
    access_token = create_access_token(db_user)

    return JSONResponse({
        "access_token": access_token,
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "role": db_user.role
        }
    })