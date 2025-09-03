# app/utils/forum_content.py
import re
from urllib.parse import urlparse, urlunparse
from fastapi import HTTPException
import httpx  # pip install httpx

IMG_MD_RE = re.compile(r'!\[[^\]]*\]\((?P<src>[^)]+)\)', re.IGNORECASE)
IMG_TAG_RE = re.compile(r'<img\b[^>]*\ssrc=["\'](?P<src>[^"\']+)["\']', re.IGNORECASE)

SAFE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_IMAGE_BYTES = 307_200           # 300 KB (png/jpg/webp)
MAX_GIF_BYTES = 1_048_576           # 1 MB
HEAD_TIMEOUT = 3.0                  # seconds
FOLLOW_REDIRECTS = True

def _normalize_and_validate_url(src: str) -> str:
    """
    Normalize protocol-relative URLs and enforce http(s).
    Returns the normalized URL string or raises HTTPException.
    """
    try:
        src = src.strip()
        u = urlparse(src)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image URL")

    # Allow protocol-relative ("//host/path") → coerce to https
    if not u.scheme and u.netloc:
        u = u._replace(scheme="https")

    scheme = (u.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http(s) images are allowed")

    # Ensure there's a hostname and a path
    if not u.netloc or not u.path:
        raise HTTPException(status_code=400, detail="Invalid image URL")

    # Extension whitelist
    if not u.path.lower().endswith(SAFE_EXTS):
        raise HTTPException(status_code=400, detail="Unsupported image type")

    return urlunparse(u)

def _best_effort_head_check(url: str) -> None:
    """
    Optional HEAD request to quickly reject obviously large/incorrect files.
    If the remote server doesn't return helpful headers, we don't block;
    we just fall back to extension checking above.
    """
    try:
        with httpx.Client(follow_redirects=FOLLOW_REDIRECTS, timeout=HEAD_TIMEOUT) as client:
            r = client.head(url)
    except Exception:
        # Don’t block on network hiccups; extension check already passed
        return

    # Content-Type: require image/* and filter svg as a conservative choice
    ctype = (r.headers.get("Content-Type") or "").lower()
    if ctype and not ctype.startswith("image/"):
        raise HTTPException(status_code=400, detail="URL is not an image")

    if "svg" in ctype:
        # keep svg out to avoid embedded scripts/complex markup
        raise HTTPException(status_code=400, detail="SVG images are not allowed")

    # Content-Length: enforce size caps if provided
    try:
        clen = int(r.headers.get("Content-Length", "0"))
    except ValueError:
        clen = 0

    if clen > 0:
        is_gif = urlparse(url).path.lower().endswith(".gif")
        limit = MAX_GIF_BYTES if is_gif else MAX_IMAGE_BYTES
        if clen > limit:
            raise HTTPException(status_code=400, detail="Image exceeds size limit")

def reject_disallowed_images(markdown: str) -> None:
    """
    Guard pasted/inline images:
      - allow http(s) only
      - require safe extensions (.png/.jpg/.jpeg/.webp/.gif)
      - best-effort HEAD check for type and size limits
    """
    def _check_one(src: str):
        url = _normalize_and_validate_url(src)
        _best_effort_head_check(url)

    text = markdown or ""
    for m in IMG_MD_RE.finditer(text):
        _check_one(m.group("src"))

    for m in IMG_TAG_RE.finditer(text):
        _check_one(m.group("src"))
