# app/routes/reading_list_routes.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.routes.auth import get_db  # ✅ use your existing DB dependency
from app.schemas.reading_list_schemas import (
    ReadingListCreate,
    ReadingListOut,
    AddSeriesRequest,
)
from app.models.reading_list import ReadingList, ReadingListItem
from app.models.user_model import User
# ⬇️ Adjust this import if your Series model lives elsewhere
from app.models.series_model import Series

# Try to read keys from your config; fall back to HS256 if ALGORITHM isn’t exported
from app.config import SECRET_KEY
try:
    from app.config import ALGORITHM  # type: ignore
except Exception:
    ALGORITHM = "HS256"

router = APIRouter(prefix="/reading-lists", tags=["reading-lists"])
MAX_LISTS_PER_USER = 2


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    """Lightweight JWT auth that matches your login/signup flow."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Try common claim keys your token might have
    user_id: Optional[int] = payload.get("id") or payload.get("user_id")
    username: Optional[str] = payload.get("username") or payload.get("sub")

    user: Optional[User] = None
    if user_id is not None:
        res = await db.execute(select(User).where(User.id == int(user_id)))
        user = res.scalar_one_or_none()
    elif username:
        res = await db.execute(select(User).where(User.username == str(username)))
        user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.get("/me", response_model=List[ReadingListOut])
async def get_my_lists(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(ReadingList)
        .where(ReadingList.user_id == current_user.id)
        .options(selectinload(ReadingList.items))
        .order_by(ReadingList.id.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ReadingListOut, status_code=status.HTTP_201_CREATED)
async def create_reading_list(
    payload: ReadingListCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Enforce per-user limit
    count_stmt = select(func.count(ReadingList.id)).where(
        ReadingList.user_id == current_user.id
    )
    count = (await session.execute(count_stmt)).scalar_one()
    if count >= MAX_LISTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can only create up to {MAX_LISTS_PER_USER} lists.",
        )

    # Unique name per user
    dup_stmt = select(ReadingList).where(
        ReadingList.user_id == current_user.id, ReadingList.name == payload.name
    )
    duplicate = (await session.execute(dup_stmt)).scalars().first()
    if duplicate:
        raise HTTPException(status_code=400, detail="You already have a list with that name.")

    new_list = ReadingList(user_id=current_user.id, name=payload.name)
    session.add(new_list)
    await session.commit()
    await session.refresh(new_list)

    # ✅ re-select with items eagerly loaded to avoid async lazy-load during serialization
    stmt = (
        select(ReadingList)
        .where(ReadingList.id == new_list.id)
        .options(selectinload(ReadingList.items))
    )
    full = (await session.execute(stmt)).scalars().first()
    return full


@router.post("/{list_id}/items", response_model=ReadingListOut)
async def add_series_to_list(
    list_id: int,
    payload: AddSeriesRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify list ownership
    list_stmt = (
        select(ReadingList)
        .where(ReadingList.id == list_id, ReadingList.user_id == current_user.id)
        .options(selectinload(ReadingList.items))
    )
    rlist = (await session.execute(list_stmt)).scalars().first()
    if not rlist:
        raise HTTPException(status_code=404, detail="List not found.")

    # Optional: verify series exists for cleaner error
    series_exists = (
        await session.execute(select(func.count(Series.id)).where(Series.id == payload.series_id))
    ).scalar_one()
    if not series_exists:
        raise HTTPException(status_code=404, detail="Series not found.")

    # Idempotent add
    exists_stmt = select(ReadingListItem).where(
        ReadingListItem.list_id == list_id, ReadingListItem.series_id == payload.series_id
    )
    existing = (await session.execute(exists_stmt)).scalars().first()
    if existing:
        return rlist

    session.add(ReadingListItem(list_id=list_id, series_id=payload.series_id))
    await session.commit()

    # Return updated list with items
    rlist = (
        await session.execute(
            select(ReadingList)
            .where(ReadingList.id == list_id)
            .options(selectinload(ReadingList.items))
        )
    ).scalars().first()
    return rlist


@router.delete("/{list_id}/items/{series_id}", response_model=ReadingListOut)
async def remove_series_from_list(
    list_id: int,
    series_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify list ownership
    list_stmt = select(ReadingList).where(
        ReadingList.id == list_id, ReadingList.user_id == current_user.id
    )
    rlist = (await session.execute(list_stmt)).scalars().first()
    if not rlist:
        raise HTTPException(status_code=404, detail="List not found.")

    # Delete row
    del_stmt = (
        delete(ReadingListItem)
        .where(ReadingListItem.list_id == list_id, ReadingListItem.series_id == series_id)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(del_stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Series not found in this list.")

    await session.commit()

    # Return updated list
    rlist = (
        await session.execute(
            select(ReadingList)
            .where(ReadingList.id == list_id)
            .options(selectinload(ReadingList.items))
        )
    ).scalars().first()
    return rlist


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    list_stmt = select(ReadingList).where(
        ReadingList.id == list_id, ReadingList.user_id == current_user.id
    )
    rlist = (await session.execute(list_stmt)).scalars().first()
    if not rlist:
        raise HTTPException(status_code=404, detail="List not found.")

    await session.delete(rlist)
    await session.commit()
