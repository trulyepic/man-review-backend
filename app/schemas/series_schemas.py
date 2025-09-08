
from pydantic import BaseModel
from enum import Enum
from fastapi import Form
from typing import Optional, Union
from decimal import Decimal

class SeriesTypeEnum(str, Enum):
    MANGA = "MANGA"
    MANHWA = "MANHWA"
    MANHUA = "MANHUA"

class SeriesStatusEnum(str, Enum):
    ONGOING = "ONGOING"
    COMPLETE = "COMPLETE"
    HIATUS = "HIATUS"
    UNKNOWN = "UNKNOWN"
    SEASON_END = "SEASON_END"

class SeriesCreate(BaseModel):
    title: str
    genre: str
    type: SeriesTypeEnum
    author: Optional[str] = ""
    artist: Optional[str] = ""
    status: Optional[SeriesStatusEnum] = None

    @classmethod
    def as_form(
            cls,
            title: str = Form(...),
            genre: str = Form(...),
            type: SeriesTypeEnum = Form(...),
            author: str = Form(""),
            artist: str = Form(""),
            status: Optional[SeriesStatusEnum] = Form(None)

    ) -> "SeriesCreate":
        return cls(title=title, genre=genre, type=type, author=author, artist=artist, status=status)


class SeriesUpdate(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    type: Optional[SeriesTypeEnum] = None
    author: Optional[str] = None
    artist: Optional[str] = None
    status: Optional[SeriesStatusEnum] = None

class SeriesOut(SeriesCreate):
    id: int
    vote_count: int
    cover_url: str

    model_config = {
        "from_attributes": True
    }

class RankedSeriesOut(SeriesOut):
    final_score: Decimal
    rank: Optional[int]  # Can be null for unranked

    model_config = {
        "from_attributes": True
    }

