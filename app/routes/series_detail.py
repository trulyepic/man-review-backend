from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_async_session
from app.models.series_model import Series
from app.models.series_detail import SeriesDetail
from app.models.user_model import User
from app.schemas.series_detail_schemas import SeriesDetailOut
from app.s3 import upload_to_s3
from app.models.user_vote import UserVote
from app.utils.token_utils import get_current_user
from fastapi.responses import JSONResponse
from sqlalchemy import func

router = APIRouter(prefix="/series-details", tags=["Series Details"])

@router.post("/", response_model=SeriesDetailOut)
async def create_or_update_series_detail(
    series_id: int = Form(...),
    synopsis: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session)
):
    series = await session.get(Series, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Upload image to S3
    file.file.seek(0)  # Make sure pointer is at start
    file_url = upload_to_s3(file.file, file.filename, file.content_type, folder=f"{series_id}/covers")

    # Check if detail already exists
    result = await session.execute(select(SeriesDetail).where(SeriesDetail.series_id == series_id))
    detail = result.scalars().first()

    if detail:
        # Update existing
        detail.synopsis = synopsis
        detail.series_cover_url = file_url
    else:
        # Create new
        detail = SeriesDetail(
            series_id=series_id,
            synopsis=synopsis,
            series_cover_url=file_url
        )
        session.add(detail)

    await session.commit()
    await session.refresh(detail)
    return detail



@router.post("/{series_id}/vote", response_model=SeriesDetailOut)
async def vote_series_detail(
    series_id: int,
    category: str = Form(...),
    score: int = Form(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    valid_categories = {
        "Story": ("story_total", "story_count"),
        "Characters": ("characters_total", "characters_count"),
        "World Building": ("worldbuilding_total", "worldbuilding_count"),
        "Art": ("art_total", "art_count"),
        "Drama / Fighting": ("drama_or_fight_total", "drama_or_fight_count")
    }

    if category not in valid_categories or not (1 <= score <= 10):
        raise HTTPException(status_code=400, detail="Invalid vote")

    detail = await session.scalar(
        select(SeriesDetail).where(SeriesDetail.series_id == series_id)
    )
    if not detail:
        raise HTTPException(status_code=404, detail="Series detail not found")

    # ❌ Already voted on this category?
    existing_vote = await session.scalar(
        select(UserVote).where(
            UserVote.user_id == user.id,
            UserVote.series_id == series_id,
            UserVote.category == category
        )
    )
    if existing_vote:
        raise HTTPException(status_code=403, detail="You already voted on this category")

    # ✅ Apply vote
    total_field, count_field = valid_categories[category]
    setattr(detail, total_field, getattr(detail, total_field) + score)
    setattr(detail, count_field, getattr(detail, count_field) + 1)

    # 🧠 Check if this is user's FIRST vote for this series
    previous_votes = await session.execute(
        select(UserVote).where(
            UserVote.user_id == user.id,
            UserVote.series_id == series_id
        )
    )
    has_prior_votes = previous_votes.first() is not None

    # ✅ Increment only on first vote
    if not has_prior_votes:
        series = await session.get(Series, series_id)
        series.vote_count = (series.vote_count or 0) + 1

    # 🗳️ Save this vote
    session.add(UserVote(
        user_id=user.id,
        series_id=series_id,
        category=category,
        score=score
    ))
    await session.commit()
    await session.refresh(detail)
    return detail



@router.get("/{series_id}", response_model=SeriesDetailOut)
async def get_series_detail(
    series_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    # Get series first (always exists in this use case)
    series = await session.get(Series, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    result = await session.execute(
        select(SeriesDetail).where(SeriesDetail.series_id == series_id)
    )
    detail = result.scalars().first()

    # Create default empty detail if not yet created
    if not detail:
        detail = SeriesDetail(
            series_id=series_id,
            synopsis="",
            series_cover_url="",  # You can also set a default placeholder image URL here
            story_total=0,
            story_count=0,
            characters_total=0,
            characters_count=0,
            worldbuilding_total=0,
            worldbuilding_count=0,
            art_total=0,
            art_count=0,
            drama_or_fight_total=0,
            drama_or_fight_count=0,
        )

    # Try to extract user from token
    user = None
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if token:
        try:
            user = await get_current_user(token=token, session=session)
        except:
            pass

    CATEGORY_LABELS = {
        "Story": "Story",
        "Characters": "Characters",
        "World Building": "World Building",
        "Art": "Art",
        "Drama / Fighting": "Drama / Fighting",
    }

    vote_scores = {}
    if user:
        results = await session.execute(
            select(UserVote.category, UserVote.score).where(
                UserVote.user_id == user.id,
                UserVote.series_id == series_id
            )
        )
        vote_scores = {
            CATEGORY_LABELS.get(row[0], row[0]): row[1]
            for row in results.all()
        }

    vote_counts = {}
    count_results = await session.execute(
        select(UserVote.category, func.count(func.distinct(UserVote.user_id)))
        .where(UserVote.series_id == series_id)
        .group_by(UserVote.category)
    )
    for cat, count in count_results:
        vote_counts[CATEGORY_LABELS.get(cat, cat)] = count

    response_data = jsonable_encoder(detail)
    response_data["vote_scores"] = vote_scores
    response_data["vote_counts"] = vote_counts
    response_data["author"] = series.author
    response_data["artist"] = series.artist

    return JSONResponse(content=response_data)


# @router.get("/{series_id}", response_model=SeriesDetailOut)
# async def get_series_detail(
#     series_id: int,
#     request: Request,
#     session: AsyncSession = Depends(get_async_session),
# ):
#     # Join SeriesDetail with Series to get author and artist
#     result = await session.execute(
#         select(SeriesDetail, Series)
#         .join(Series, Series.id == SeriesDetail.series_id)
#         .where(SeriesDetail.series_id == series_id)
#     )
#     row = result.first()
#     if not row:
#         raise HTTPException(status_code=404, detail="Series detail not found")
#
#     detail, series = row
#
#     # Try to extract user from token
#     user = None
#     token = request.headers.get("authorization", "").replace("Bearer ", "")
#     if token:
#         try:
#             user = await get_current_user(token=token, session=session)
#         except:
#             pass
#
#     # Capitalized category keys for frontend consistency
#     CATEGORY_LABELS = {
#         "Story": "Story",
#         "Characters": "Characters",
#         "World Building": "World Building",
#         "Art": "Art",
#         "Drama / Fighting": "Drama / Fighting",
#     }
#
#     # Get the current user's actual votes
#     vote_scores = {}
#     if user:
#         results = await session.execute(
#             select(UserVote.category, UserVote.score).where(
#                 UserVote.user_id == user.id,
#                 UserVote.series_id == series_id
#             )
#         )
#         vote_scores = {
#             CATEGORY_LABELS[row[0]]: row[1]
#             for row in results.all()
#             if row[0] in CATEGORY_LABELS
#         }
#
#     # Get vote counts per category (distinct users)
#     vote_counts = {}
#     count_results = await session.execute(
#         select(UserVote.category, func.count(func.distinct(UserVote.user_id)))
#         .where(UserVote.series_id == series_id)
#         .group_by(UserVote.category)
#     )
#     for cat, count in count_results:
#         vote_counts[CATEGORY_LABELS.get(cat, cat)] = count
#
#     # Prepare response with extra author/artist fields
#     response_data = jsonable_encoder(detail)
#     response_data["vote_scores"] = vote_scores
#     response_data["vote_counts"] = vote_counts
#     response_data["author"] = series.author
#     response_data["artist"] = series.artist
#
#     return JSONResponse(content=response_data)



