from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "man_review"}

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="GENERAL")  # GENERAL or ADMIN
    email = Column(String, unique=True, index=True, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False, server_default="false")

