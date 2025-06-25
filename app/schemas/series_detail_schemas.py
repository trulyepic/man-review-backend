from pydantic import BaseModel
from typing import Optional, Dict

class SeriesDetailCreate(BaseModel):
    series_id: int
    synopsis: str

class SeriesDetailOut(BaseModel):
    id: int
    series_id: int
    synopsis: str
    series_cover_url: str

    author: Optional[str] = None
    artist: Optional[str] = None

    story_total: int = 0
    story_count: int = 0
    characters_total: int = 0
    characters_count: int = 0
    worldbuilding_total: int = 0
    worldbuilding_count: int = 0
    art_total: int = 0
    art_count: int = 0
    drama_or_fight_total: int = 0
    drama_or_fight_count: int = 0

    vote_scores: Optional[Dict[str, int]] = {}
    vote_counts: Optional[Dict[str, int]] = {}

    model_config = {
        "from_attributes": True
    }
