# app/models/forum_media_model.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.forum_model import ForumThread, ForumPost  # if you reference in relationships
from app.models.user_model import User

SCHEMA = "man_review"

class ForumMedia(Base):
    __tablename__ = "forum_media"
    __table_args__ = ({"schema": SCHEMA},)

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    thread_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    url = Column(Text, nullable=False)
    mime_type = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # optional relationships
    user = relationship("User", lazy="joined")
    thread = relationship("ForumThread", lazy="joined")
    post = relationship("ForumPost", lazy="joined")
