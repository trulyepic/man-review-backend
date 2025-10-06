from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user_model import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
ACCESS_TOKEN_EXPIRE_MINUTES =4320 #3 days # 480 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# def create_access_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt
# def create_access_token(user: User):
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode = {
#         "id": user.id,          # ✅ this is what your get_current_user expects
#         "sub": user.username,   # Optional, helps for auditing/logs
#         "role": user.role,      # Optional, if you use role-based access
#         "exp": expire
#     }
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

def _get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        # Fail fast with a clear message instead of a generic 500
        raise RuntimeError("SECRET_KEY is not configured in the backend environment")
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY is too short; use at least 32 characters")
    return secret

def create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "id": user.id,         # what get_current_user expects
        "sub": user.username,  # helpful for auditing/logs
        "role": user.role,     # if you use role-based access
        "exp": expire,
    }
    try:
        return jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    except Exception as e:
        raise RuntimeError(f"JWT encode failed: {e}")



async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")  # 🔑 Uses the updated token payload
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await session.get(User, user_id)
    if not user:
        raise credentials_exception

    return user  # Returns SQLAlchemy user model