from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class ReadingListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class ReadingListItemOut(BaseModel):
    series_id: int
    left_off_chapter: Optional[str] = None

    class Config:
        from_attributes = True

class ReadingListOut(BaseModel):
    id: int
    name: str
    is_public: bool
    share_token: UUID
    # share_token: str
    items: List[ReadingListItemOut] = []

    class Config:
        from_attributes = True

class AddSeriesRequest(BaseModel):
    series_id: int
    left_off_chapter: Optional[str] = Field(default=None, max_length=50)

class UpdateReadingListItemRequest(BaseModel):
    left_off_chapter: Optional[str] = Field(default=None, max_length=50)

class PublicReadingListOut(BaseModel):
    name: str
    items: List[ReadingListItemOut] = []
