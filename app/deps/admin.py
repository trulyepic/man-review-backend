# app/deps/admin.py
from fastapi import Depends, HTTPException, status
from app.models.user_model import User
from app.utils.token_utils import get_current_user

async def get_user_from_token(user: User = Depends(get_current_user)) -> User:
    """
    Convenience dependency that simply returns the authenticated user
    using your existing token_utils.get_current_user.
    """
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Requires the authenticated user to have role=ADMIN.
    Raises 403 if not an admin.
    """
    if getattr(user, "role", "GENERAL") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
