from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, String
from app.database import Base

class UserVote(Base):
    __tablename__ = "user_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "series_id", "category", name="unique_user_vote"),
        {"schema": "man_review"},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("man_review.users.id"))
    series_id = Column(Integer, ForeignKey("man_review.series.id"))
    category = Column(String, nullable=False)  # ✅ New
    score = Column(Integer, nullable=False)

