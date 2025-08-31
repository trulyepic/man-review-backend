from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class SeriesRefOut(BaseModel):
    series_id: int
    title: Optional[str] = None
    cover_url: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None


class ForumPostOut(BaseModel):
    id: int
    author_username: Optional[str] = None
    content_markdown: str
    created_at: str
    updated_at: str
    series_refs: List[SeriesRefOut] = []
    parent_id: Optional[int] = None


class ForumThreadOut(BaseModel):
    id: int
    title: str
    author_username: Optional[str] = None
    created_at: str
    updated_at: str
    post_count: int
    last_post_at: str
    series_refs: List[SeriesRefOut] = []
    locked: bool = False
    latest_first: bool = False


class CreateThreadIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    first_post_markdown: str = Field(min_length=1)
    series_ids: List[int] = []



class CreatePostIn(BaseModel):
    content_markdown: str = Field(min_length=1)
    series_ids: List[int] = Field(default_factory=list)   # <— safer default
    parent_id: Optional[int] = None

class ThreadSettingsIn(BaseModel):
    latest_first: Optional[bool] = None


class UpdatePostIn(BaseModel):
    content_markdown: str
    series_ids: List[int] = []

class UpdateThreadIn(BaseModel):
    # All optional so the client can send only what changed
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    first_post_markdown: Optional[str] = Field(default=None, min_length=1)
    # Optional: only replace header refs when provided
    series_ids: Optional[List[int]] = None
