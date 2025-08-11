from pydantic import BaseModel, Field
from typing import List

class ReadingListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class ReadingListItemOut(BaseModel):
    series_id: int

    class Config:
        from_attributes = True

class ReadingListOut(BaseModel):
    id: int
    name: str
    items: List[ReadingListItemOut] = []

    class Config:
        from_attributes = True

class AddSeriesRequest(BaseModel):
    series_id: int
