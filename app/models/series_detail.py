from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SeriesDetail(Base):
    __tablename__ = "series_details"
    __table_args__ = {"schema": "man_review"}

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("man_review.series.id", ondelete="CASCADE"), unique=True)
    synopsis = Column(String)
    series_cover_url = Column(String)

    # Ratings fields
    story_total = Column(Integer, default=0)
    story_count = Column(Integer, default=0)

    characters_total = Column(Integer, default=0)
    characters_count = Column(Integer, default=0)

    worldbuilding_total = Column(Integer, default=0)
    worldbuilding_count = Column(Integer, default=0)

    art_total = Column(Integer, default=0)
    art_count = Column(Integer, default=0)

    drama_or_fight_total = Column(Integer, default=0)
    drama_or_fight_count = Column(Integer, default=0)

    series = relationship("Series", back_populates="detail")
