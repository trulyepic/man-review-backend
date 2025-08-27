from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.database import get_async_session
from app.models.forum_model import ForumThread, ForumPost, ForumSeriesRef
from app.models.series_model import Series
from app.models.user_model import User

from app.schemas.forum_schemas import (
    ForumThreadOut, ForumPostOut, CreateThreadIn, CreatePostIn, SeriesRefOut,
)

# ✅ Use your existing token utils (no changes there)
from app.utils.token_utils import get_current_user, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(prefix="/forum", tags=["forum"])

# ------------------------------
# helpers
# ------------------------------
def _is_admin(user: "User") -> bool:
    return (getattr(user, "role", "") or "").upper() == "ADMIN"

async def _post_to_plain_dict(p: ForumPost, db: AsyncSession) -> dict:
    refs = await db.execute(
        select(ForumSeriesRef, Series)
        .join(Series, Series.id == ForumSeriesRef.series_id)
        .where(ForumSeriesRef.post_id == p.id)
    )
    srefs = []
    for (_ref, s) in refs.all():
        srefs.append({
            "series_id": s.id,
            "title": s.title,
            "cover_url": s.cover_url,
            "type": s.type,
            "status": s.status,
        })

    author_username = None
    if p.author_id:
        u = await db.get(User, p.author_id)
        author_username = getattr(u, "username", None) if u else None

    # Always include parent_id; use 0 for top-level
    return {
        "id": p.id,
        "author_username": author_username,
        "content_markdown": p.content_markdown,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
        "series_refs": srefs,
        "parent_id": int(p.parent_id) if p.parent_id is not None else 0,
    }

def dump_model(m):
    return m.model_dump(exclude_none=False) if hasattr(m, "model_dump") else m.dict(exclude_none=False)

# ------------------------------
# Local optional-user helper ONLY in this file
# ------------------------------
async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            return None
    except JWTError:
        return None

    user = await db.get(User, user_id)
    return user

# ------------------------------
# Mappers
# ------------------------------
async def _thread_to_out(t: ForumThread, db: AsyncSession) -> ForumThreadOut:
    author_username: Optional[str] = None
    if t.author_id:
        u = await db.get(User, t.author_id)
        author_username = getattr(u, "username", None) if u else None

    refs = await db.execute(
        select(ForumSeriesRef, Series)
        .join(Series, Series.id == ForumSeriesRef.series_id)
        .where(ForumSeriesRef.thread_id == t.id, ForumSeriesRef.post_id == None)
    )
    srefs = [
        SeriesRefOut(
            series_id=s.id,
            title=s.title,
            cover_url=s.cover_url,
            type=s.type,
            status=s.status,
        )
        for (_ref, s) in refs.all()
    ]

    return ForumThreadOut(
        id=t.id,
        title=t.title,
        author_username=author_username,
        created_at=str(t.created_at),
        updated_at=str(t.updated_at),
        post_count=t.post_count or 0,
        last_post_at=str(t.last_post_at),
        series_refs=srefs,
    )

async def _post_to_out(p: ForumPost, db: AsyncSession) -> ForumPostOut:
    refs = await db.execute(
        select(ForumSeriesRef, Series)
        .join(Series, Series.id == ForumSeriesRef.series_id)
        .where(ForumSeriesRef.post_id == p.id)
    )
    srefs = [
        SeriesRefOut(
            series_id=s.id,
            title=s.title,
            cover_url=s.cover_url,
            type=s.type,
            status=s.status,
        )
        for (_ref, s) in refs.all()
    ]

    author_username: Optional[str] = None
    if p.author_id:
        u = await db.get(User, p.author_id)
        author_username = getattr(u, "username", None) if u else None

    return ForumPostOut(
        id=p.id,
        author_username=author_username,
        content_markdown=p.content_markdown,
        created_at=str(p.created_at),
        updated_at=str(p.updated_at),
        series_refs=srefs,
        parent_id=p.parent_id if p.parent_id is not None else 0,
    )

# ------------------------------
# Routes
# ------------------------------
@router.get("/threads", response_model=List[ForumThreadOut])
async def list_threads(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_async_session),
    _viewer: Optional[User] = Depends(get_current_user_optional),
):
    stmt = select(ForumThread).order_by(ForumThread.updated_at.desc())
    if q:
        stmt = select(ForumThread).where(ForumThread.title.ilike(f"%{q}%")).order_by(
            ForumThread.updated_at.desc()
        )

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _thread_to_out(t, db) for t in rows]

@router.post("/threads", response_model=ForumThreadOut)
async def create_thread(
    payload: CreateThreadIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    # 🔒 limit: max 10 threads per user
    existing_count = (
        await db.execute(
            select(func.count(ForumThread.id)).where(ForumThread.author_id == user.id)
        )
    ).scalar_one()
    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Thread limit reached (10). Delete an existing thread to create a new one.",
        )

    thread = ForumThread(title=payload.title, author_id=user.id)
    db.add(thread)
    await db.flush()  # get thread.id

    post = ForumPost(
        thread_id=thread.id,
        author_id=user.id,
        content_markdown=payload.first_post_markdown,
    )
    db.add(post)

    for sid in payload.series_ids or []:
        db.add(ForumSeriesRef(thread_id=thread.id, post_id=None, series_id=sid))

    thread.post_count = 1
    thread.last_post_at = func.now()

    await db.commit()
    await db.refresh(thread)

    return await _thread_to_out(thread, db)

@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_async_session),
    _viewer: Optional[User] = Depends(get_current_user_optional),  # optional
):
    t = await db.get(ForumThread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")

    header_refs = await db.execute(
        select(ForumSeriesRef, Series)
        .join(Series, Series.id == ForumSeriesRef.series_id)
        .where(ForumSeriesRef.thread_id == thread_id, ForumSeriesRef.post_id == None)
    )
    header = [
        {
            "series_id": s.id,
            "title": s.title,
            "cover_url": s.cover_url,
            "type": s.type,
            "status": s.status,
        }
        for (_ref, s) in header_refs.all()
    ]

    posts = (
        await db.execute(
            select(ForumPost)
            .where(ForumPost.thread_id == thread_id)
            .order_by(ForumPost.created_at.asc())
        )
    ).scalars().all()

    posts_out = [await _post_to_plain_dict(p, db) for p in posts]

    return {
        "thread": {
            "id": t.id,
            "title": t.title,
            "author_username": None,
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
            "post_count": t.post_count or 0,
            "last_post_at": str(t.last_post_at),
            "series_refs": header,
        },
        "posts": posts_out,
    }

@router.post("/threads/{thread_id}/posts")
async def create_post(
    thread_id: int,
    payload: CreatePostIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    thread = await db.get(ForumThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    parent_id = payload.parent_id
    if parent_id is not None:
        parent = await db.get(ForumPost, parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent post not found")
        if parent.thread_id != thread_id:
            raise HTTPException(status_code=400, detail="Parent post is from another thread")

    post = ForumPost(
        thread_id=thread_id,
        author_id=user.id,
        content_markdown=payload.content_markdown,
        parent_id=parent_id,
    )
    db.add(post)
    await db.flush()

    for sid in (payload.series_ids or []):
        db.add(ForumSeriesRef(thread_id=thread_id, post_id=post.id, series_id=sid))

    thread.post_count = (thread.post_count or 0) + 1
    thread.last_post_at = func.now()

    await db.commit()
    await db.refresh(post)

    return await _post_to_plain_dict(post, db)

@router.get("/series-search", response_model=List[SeriesRefOut])
async def forum_series_search(
    q: str = Query(..., min_length=1),
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
):
    rows = (
        await db.execute(
            select(Series).where(Series.title.ilike(f"%{q}%")).limit(limit)
        )
    ).scalars().all()
    return [
        SeriesRefOut(
            series_id=s.id,
            title=s.title,
            cover_url=s.cover_url,
            type=s.type,
            status=s.status,
        )
        for s in rows
    ]

# ------------------------------
# Deletes (owner-or-admin)
# ------------------------------
@router.delete("/threads/{thread_id}/posts/{post_id}", status_code=204)
async def delete_post(
    thread_id: int,
    post_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    post = await db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.thread_id != thread_id:
        raise HTTPException(status_code=400, detail="Post is not in this thread")

    # Only admins or the author of the post
    if not (_is_admin(user) or post.author_id == user.id):
        raise HTTPException(status_code=403, detail="Admins or the post owner may delete this post.")

    # Prevent deleting the original post via this endpoint
    first_post_id = (
        await db.execute(
            select(ForumPost.id)
            .where(ForumPost.thread_id == thread_id)
            .order_by(ForumPost.created_at.asc())
            .limit(1)
        )
    ).scalar_one()
    if post.id == first_post_id:
        raise HTTPException(status_code=400, detail="Delete the thread to remove the original post.")

    thread = await db.get(ForumThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    await db.delete(post)   # cascades to children via ON DELETE CASCADE
    await db.flush()

    # refresh thread counters
    total_posts = (
        await db.execute(
            select(func.count()).select_from(ForumPost).where(ForumPost.thread_id == thread_id)
        )
    ).scalar_one()
    last_post_at = (
        await db.execute(
            select(func.max(ForumPost.created_at)).where(ForumPost.thread_id == thread_id)
        )
    ).scalar_one()

    thread.post_count = int(total_posts or 0)
    thread.last_post_at = last_post_at or thread.created_at

    await db.commit()
    return Response(status_code=204)

@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    thread = await db.get(ForumThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Admins OR owner of the thread
    if not (_is_admin(user) or thread.author_id == user.id):
        raise HTTPException(status_code=403, detail="Admins or the thread owner may delete this thread.")

    await db.delete(thread)  # cascades to posts + series refs
    await db.commit()
    return Response(status_code=204)

@router.delete("/threads/{thread_id}/posts/{post_id}/mine", status_code=204)
async def delete_my_post(
    thread_id: int,
    post_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    post = await db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.thread_id != thread_id:
        raise HTTPException(status_code=400, detail="Post is not in this thread")
    # must be author or admin
    if (user.role or "").upper() != "ADMIN" and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.delete(post)
    await db.flush()

    thread = await db.get(ForumThread, thread_id)
    if thread:
        total_posts = (
            await db.execute(
                select(func.count()).select_from(ForumPost).where(ForumPost.thread_id == thread_id)
            )
        ).scalar_one()
        last_post_at = (
            await db.execute(
                select(func.max(ForumPost.created_at)).where(ForumPost.thread_id == thread_id)
            )
        ).scalar_one()

        thread.post_count = int(total_posts or 0)
        thread.last_post_at = last_post_at or thread.created_at

    await db.commit()
    return Response(status_code=204)

