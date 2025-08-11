# app/models/reading_list.py
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class ReadingList(Base):
    __tablename__ = "reading_lists"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_reading_lists_user_name"),
        {"schema": "man_review"},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("man_review.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)

    items = relationship(
        "ReadingListItem",
        cascade="all, delete-orphan",
        back_populates="reading_list",
    )


class ReadingListItem(Base):
    __tablename__ = "reading_list_items"
    __table_args__ = (
        UniqueConstraint("list_id", "series_id", name="uq_list_series"),
        {"schema": "man_review"},
    )

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(
        Integer,
        ForeignKey("man_review.reading_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_id = Column(
        Integer,
        ForeignKey("man_review.series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reading_list = relationship("ReadingList", back_populates="items")
