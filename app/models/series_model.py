
from sqlalchemy import Column, Integer, String, Enum as SqlEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class SeriesType(enum.Enum):
    MANGA = "MANGA"
    MANHWA = "MANHWA"
    MANHUA = "MANHUA"

class SeriesStatus(enum.Enum):
    ONGOING = "ONGOING"
    COMPLETE = "COMPLETE"
    HIATUS = "HIATUS"
    UNKNOWN = "UNKNOWN"

class Series(Base):
    __tablename__ = 'series'
    __table_args__ = {"schema": "man_review"}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    genre = Column(String)
    vote_count = Column(Integer, default=0)
    cover_url = Column(String)
    type = Column(SqlEnum(SeriesType), nullable=False)
    author = Column(String)
    artist = Column(String)

    status = Column(
        SqlEnum(
            SeriesStatus,
            name="series_status",
            schema="man_review",
            create_type=False,  # don't try to create; we already created via SQL
        ),
        nullable=True,
    )

    # Relationship to SeriesDetail
    detail = relationship(
        "SeriesDetail",
        back_populates="series",
        uselist=False,
        cascade="all, delete-orphan"
    )