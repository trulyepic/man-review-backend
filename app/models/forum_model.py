
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
    UniqueConstraint, Boolean,
text
)
from sqlalchemy.orm import relationship
from app.database import Base

SCHEMA = "man_review"

class ForumThread(Base):
    __tablename__ = "forum_threads"
    __table_args__ = (
        # add any extra constraints here if needed
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)

    # user is in man_review.users
    author_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # denormalized counters for faster thread list
    post_count = Column(Integer, nullable=False, server_default="0")
    last_post_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked = Column(Boolean, nullable=False, server_default=text("false"))

    # relationships
    posts = relationship(
        "ForumPost",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    series_refs = relationship(
        "ForumSeriesRef",
        back_populates="thread",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ForumPost(Base):
    __tablename__ = "forum_posts"
    __table_args__ = ({"schema": SCHEMA},)

    id = Column(Integer, primary_key=True, index=True)

    thread_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_posts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content_markdown = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationships
    thread = relationship("ForumThread", back_populates="posts")
    series_refs = relationship(
        "ForumSeriesRef",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    parent = relationship("ForumPost", remote_side=[id], backref="replies")


class ForumSeriesRef(Base):
    __tablename__ = "forum_series_refs"
    __table_args__ = (
        # Optional: prevent duplicate (thread_id, post_id, series_id) triples
        # UniqueConstraint("thread_id", "post_id", "series_id", name="uq_forum_series_ref"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True, index=True)

    thread_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Can be null when the reference is attached to the thread header (not a specific post)
    post_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.forum_posts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Points to your Series table
    series_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # relationships
    thread = relationship("ForumThread", back_populates="series_refs")
    post = relationship("ForumPost", back_populates="series_refs")
