# app/routes/forum_media_routes.py
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple
from PIL import Image
import io
from typing import cast

from app.database import get_async_session
from app.s3 import upload_to_s3
from app.utils.token_utils import get_current_user
from app.models.user_model import User
from app.models.forum_media_model import ForumMedia
from app.config import AWS_BUCKET_NAME, AWS_REGION
 # whatever your s3 helper path is
from app.moderation.profanity import ensure_clean

router = APIRouter(prefix="/forum/media", tags=["forum-media"])

# Tiny limits (mirror DB + client)
MAX_BYTES_IMAGE = 307_200      # 300 KB (png/jpeg/webp)
MAX_BYTES_GIF   = 1_048_576    # 1 MB
MAX_WH_IMAGE    = 1024         # max width/height for non-GIF
MAX_WH_GIF      = 512          # max width/height for GIF
ALLOWED_MIMES   = {"image/png", "image/jpeg", "image/webp", "image/gif"}

def sniff_image_dims(data: bytes) -> Optional[Tuple[int, int]]:
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            return int(im.width), int(im.height)
    except Exception:
        return None

@router.post("/upload")
async def upload_forum_image_or_gif(
    thread_id: int = Form(...),
    file: UploadFile = File(...),
    post_id: Optional[int] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Unsupported image type.")

    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty file.")

    # size limits
    if file.content_type == "image/gif":
        if len(blob) > MAX_BYTES_GIF:
            raise HTTPException(status_code=400, detail="GIF too large (max 1 MB).")
    else:
        if len(blob) > MAX_BYTES_IMAGE:
            raise HTTPException(status_code=400, detail="Image too large (max 300 KB).")

    dims = sniff_image_dims(blob)
    width: Optional[int] = None
    height: Optional[int] = None
    if dims:
        width, height = dims
        if file.content_type == "image/gif":
            if width > MAX_WH_GIF or height > MAX_WH_GIF:
                raise HTTPException(status_code=400, detail="GIF dimensions too large (max 512×512).")
        else:
            if width > MAX_WH_IMAGE or height > MAX_WH_IMAGE:
                raise HTTPException(status_code=400, detail="Image dimensions too large (max 1024×1024).")

    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Unsupported image type.")

    mime: str = cast(str, file.content_type)

    # upload to S3
    url = upload_to_s3(
        io.BytesIO(blob),
        filename=file.filename or "upload",
        content_type=mime,
        folder="forum",
        subfolder="media",
    )

    # persist metadata
    media = ForumMedia(
        user_id=user.id,
        thread_id=thread_id,
        post_id=post_id,
        url=url,
        mime_type=mime,
        size_bytes=len(blob),
        width=width,
        height=height,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return {
        "id": media.id,
        "url": media.url,
        "mime": media.mime_type,
        "size": media.size_bytes,
        "width": media.width,
        "height": media.height,
        "thread_id": media.thread_id,
        "post_id": media.post_id,
    }
