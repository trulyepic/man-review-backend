# app/utils/forum_content.py
import re
from urllib.parse import urlparse
from fastapi import HTTPException

IMG_MD_RE = re.compile(r'!\[[^\]]*\]\((?P<src>[^)]+)\)', re.IGNORECASE)
IMG_TAG_RE = re.compile(r'<img\b[^>]*\ssrc=["\'](?P<src>[^"\']+)["\']', re.IGNORECASE)

def reject_disallowed_images(markdown: str) -> None:
    """
    Server-side guard: allow ANY http(s) images.
    Reject only data:, javascript:, file:, or other unsafe schemes.
    """
    def _check(src: str):
        try:
            u = urlparse(src.strip())
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image URL")

        scheme = u.scheme.lower()
        if scheme not in ("http", "https", ""):  # allow protocol-relative too (//host/img.png)
            raise HTTPException(status_code=400, detail="Only http(s) images are allowed")

    for m in IMG_MD_RE.finditer(markdown or ""):
        _check(m.group("src"))

    for m in IMG_TAG_RE.finditer(markdown or ""):
        _check(m.group("src"))
