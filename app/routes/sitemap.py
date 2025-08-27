from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import List, Tuple

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ⬇️ adjust these imports if your module names differ
from app.database import get_async_session
from app.models.forum_model import ForumThread  # has id, updated_at, last_post_at

router = APIRouter(tags=["Sitemaps"])

# --- Config ---
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "https://toonranks.com").rstrip("/")
URLS_PER_SITEMAP = int(os.getenv("SITEMAP_URLS_PER_FILE", "50000"))

STATIC_SITEMAP_URL = f"{PUBLIC_ORIGIN}/sitemap-static.xml"


def _fmt_lastmod(d: datetime | None) -> str:
    """
    Return a sitemap-safe date string (YYYY-MM-DD).
    Using date-only is fine and avoids timezone headaches.
    """
    if not d:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        if d.tzinfo is None:
            # treat naive as UTC
            d = d.replace(tzinfo=timezone.utc)
        return d.date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def _thread_loc(thread_id: int) -> str:
    return f"{PUBLIC_ORIGIN}/forum/{thread_id}"


def _render_urlset(urls: List[Tuple[str, str]]) -> str:
    # urls: list of (loc, lastmod)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def _render_sitemap_index(sitemaps: List[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc in sitemaps:
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("  </sitemap>")
    lines.append("</sitemapindex>")
    return "\n".join(lines)


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_index(session: AsyncSession = Depends(get_async_session)) -> Response:
    """
    Sitemap index:
      - /sitemap-static.xml  (your fixed pages)
      - /sitemaps/forum-1.xml, /sitemaps/forum-2.xml, ...
    """
    total_threads = await session.scalar(select(func.count(ForumThread.id)))
    total_threads = total_threads or 0

    sitemaps: List[str] = [STATIC_SITEMAP_URL]

    if total_threads > 0:
        num_files = math.ceil(total_threads / URLS_PER_SITEMAP)
        sitemaps.extend(
            f"{PUBLIC_ORIGIN}/sitemaps/forum-{i}.xml" for i in range(1, num_files + 1)
        )

    xml = _render_sitemap_index(sitemaps)
    return Response(content=xml, media_type="application/xml")


@router.get("/sitemaps/forum-{page}.xml", include_in_schema=False)
async def forum_sitemap_page(page: int, session: AsyncSession = Depends(get_async_session)) -> Response:
    """
    One paginated forum sitemap (1-based).
    """
    if page < 1:
        return Response(status_code=404)

    offset = (page - 1) * URLS_PER_SITEMAP

    stmt = (
        select(
            ForumThread.id.label("id"),
            func.coalesce(ForumThread.last_post_at, ForumThread.updated_at).label("lastmod"),
        )
        .order_by(ForumThread.id.asc())
        .limit(URLS_PER_SITEMAP)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).all()
    if not rows:
        return Response(status_code=404)

    urls = [(_thread_loc(r.id), _fmt_lastmod(r.lastmod)) for r in rows]
    xml = _render_urlset(urls)
    return Response(content=xml, media_type="application/xml")


# --- Optional: serve a small static sitemap from code ---
# If you already host a static XML file at /sitemap-static.xml via CDN/Nginx, you can remove this route.
_STATIC_URLSET = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- Homepage -->
  <url><loc>{PUBLIC_ORIGIN}/</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>

  <!-- Forum index -->
  <url><loc>{PUBLIC_ORIGIN}/forum</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>

  <!-- Filtered Pages -->
  <url><loc>{PUBLIC_ORIGIN}/type/MANHWA</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>
  <url><loc>{PUBLIC_ORIGIN}/type/MANGA</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>
  <url><loc>{PUBLIC_ORIGIN}/type/MANHUA</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>

  <!-- Content pages -->
  <url><loc>{PUBLIC_ORIGIN}/contact</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>
  <url><loc>{PUBLIC_ORIGIN}/about</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>
  <url><loc>{PUBLIC_ORIGIN}/how-rankings-work</loc><lastmod>{datetime.utcnow().date().isoformat()}</lastmod></url>
</urlset>
""".strip()


@router.get("/sitemap-static.xml", include_in_schema=False)
async def sitemap_static() -> Response:
    return Response(content=_STATIC_URLSET, media_type="application/xml")
