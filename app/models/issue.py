from sqlalchemy import Column, Integer, String, Text, Enum as SqlEnum, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
import enum

class IssueType(enum.Enum):
    BUG = "BUG"
    FEATURE = "FEATURE"
    CONTENT = "CONTENT"
    OTHER = "OTHER"

class IssueStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    FIXED = "FIXED"
    WONT_FIX = "WONT_FIX"

class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = {"schema": "man_review"}

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SqlEnum(IssueType, name="issue_type", schema="man_review"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    page_url = Column(String(1024))
    email = Column(String(320))
    screenshot_url = Column(String(2048))

    # we keep it nullable because anyone can report anonymously
    user_id = Column(Integer, ForeignKey("man_review.users.id"), nullable=True)
    user_agent = Column(String(512))

    status = Column(SqlEnum(IssueStatus, name="issue_status", schema="man_review"), nullable=False,
                    default=IssueStatus.OPEN)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
