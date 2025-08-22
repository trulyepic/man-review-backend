from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Literal
from datetime import datetime

from app.models.issue import IssueType, IssueStatus

IssueTypeLiteral = Literal["BUG", "FEATURE", "CONTENT", "OTHER"]

class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    type: IssueType
    title: str
    description: str
    page_url: Optional[str] = None
    email: Optional[str] = None
    screenshot_url: Optional[str] = None
    user_id: Optional[int] = None
    user_agent: Optional[str] = None
    created_at: datetime

    status: IssueStatus  # NEW
    admin_notes: Optional[str] = None

    updated_at: datetime

class IssueStatusUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: IssueStatus
    admin_notes: Optional[str] = None

    # class Config:
    #     from_attributes = True
