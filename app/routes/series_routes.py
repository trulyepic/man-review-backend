from http.client import HTTPException
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, get_async_session
from app.models.series_detail import SeriesDetail
from app.models.series_model import Series
from app.schemas.series_schemas import SeriesCreate, SeriesOut, SeriesUpdate, RankedSeriesOut
from app.s3 import upload_to_s3, delete_from_s3
from urllib.parse import urlparse
from fastapi import Query



def extract_s3_key(cover_url: str) -> str:
    parsed = urlparse(cover_url)
    return parsed.path.lstrip("/")
router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.delete("/series/{series_id}", status_code=204)
async def delete_series(series_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch the series record
    result = await db.execute(select(Series).where(Series.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Extract S3 object key from URL and delete it
    if series.cover_url:
        try:
            key = extract_s3_key(series.cover_url)
            delete_from_s3(key)
        except Exception as e:
            print(f"Warning: Failed to delete image from S3: {e}")

    await db.delete(series)
    await db.commit()

@router.post("/series/", response_model=SeriesOut)
async def create_series(
    series: SeriesCreate = Depends(SeriesCreate.as_form),
    cover: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    image_url = upload_to_s3(cover.file, cover.filename, cover.content_type, folder=series.title)

    new_series = Series(
        title=series.title,
        genre=series.genre,
        type=series.type.name,  # Convert Enum to string
        cover_url=image_url,
        author=series.author,
        artist=series.artist
    )

    db.add(new_series)
    await db.commit()
    await db.refresh(new_series)
    return new_series


@router.get("/series/", response_model=list[SeriesOut])
async def list_series(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Series))
    return result.scalars().all()


@router.put("/{series_id}", response_model=SeriesOut)
async def update_series(
    series_id: int,
    series_data: SeriesUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Series).where(Series.id == series_id))
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    for field, value in series_data.dict(exclude_unset=True).items():
        setattr(series, field, value)

    await session.commit()
    await session.refresh(series)
    return series


from typing import Optional

@router.get("/series/rankings", response_model=List[RankedSeriesOut])
async def get_ranked_series(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Series, SeriesDetail).join(
        SeriesDetail, Series.id == SeriesDetail.series_id, isouter=True
    )

    if type:
        stmt = stmt.where(Series.type == type.upper())

    query = await db.execute(stmt)
    results = query.all()
    print(f"🔍 Total results from DB (joined): {len(results)}")

    ranked_series = []
    for series, detail in results:
        def safe_avg(total, count):
            return total / count if count else 0

        if detail:
            story = safe_avg(detail.story_total, detail.story_count)
            chars = safe_avg(detail.characters_total, detail.characters_count)
            world = safe_avg(detail.worldbuilding_total, detail.worldbuilding_count)
            art = safe_avg(detail.art_total, detail.art_count)
            drama = safe_avg(detail.drama_or_fight_total, detail.drama_or_fight_count)
            final_score = round((story + chars + world + art + drama) / 5, 2)
        else:
            final_score = 0.0

        ranked_series.append({
            "id": series.id,
            "title": series.title,
            "genre": series.genre,
            "type": series.type,
            "author": series.author,
            "artist": series.artist,
            "cover_url": series.cover_url,
            "vote_count": series.vote_count or 0,
            "final_score": final_score,
        })

    # Split and sort
    ranked = [s for s in ranked_series if s["final_score"] > 0]
    unranked = [s for s in ranked_series if s["final_score"] == 0]

    print(f"🏆 Ranked series: {len(ranked)}")
    print(f"❌ Unranked series: {len(unranked)}")

    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    for idx, s in enumerate(ranked):
        s["rank"] = idx + 1
    for s in unranked:
        s["rank"] = None

    final_output = ranked + unranked

    start = (page - 1) * page_size
    end = start + page_size
    print(f"📦 Returning {len(final_output[start:end])} items for page {page} (range {start}:{end})")
    return final_output[start:end]





# @router.get("/series/rankings", response_model=List[SeriesOut])
# async def get_ranked_series(db: AsyncSession = Depends(get_db)):
#     query = await db.execute(
#         select(Series, SeriesDetail).join(SeriesDetail, Series.id == SeriesDetail.series_id, isouter=True)
#     )
#     results = query.all()
#
#     ranked_series = []
#     for series, detail in results:
#         # Compute average for each category if counts exist
#         def safe_avg(total, count):
#             return total / count if count else 0
#
#         if detail:
#             story = safe_avg(detail.story_total, detail.story_count)
#             chars = safe_avg(detail.characters_total, detail.characters_count)
#             world = safe_avg(detail.worldbuilding_total, detail.worldbuilding_count)
#             art = safe_avg(detail.art_total, detail.art_count)
#             drama = safe_avg(detail.drama_or_fight_total, detail.drama_or_fight_count)
#             final_score = round((story + chars + world + art + drama) / 5, 2)
#         else:
#             final_score = 0.0
#
#         ranked_series.append({
#             "id": series.id,
#             "title": series.title,
#             "genre": series.genre,
#             "type": series.type,
#             "author": series.author,
#             "artist": series.artist,
#             "cover_url": series.cover_url,
#             "vote_count": series.vote_count or 0,
#             "final_score": final_score,
#         })
#
#     # Sort ranked series (highest score first)
#     ranked_series.sort(key=lambda x: x["final_score"], reverse=True)
#
#     # Assign dynamic rank; if score is 0, show as unranked
#     for idx, series in enumerate(ranked_series):
#         series["rank"] = idx + 1 if series["final_score"] > 0 else None
#
#     return ranked_series
