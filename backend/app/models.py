import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class Platform(str, enum.Enum):
    leetcode = "leetcode"
    codeforces = "codeforces"
    codechef = "codechef"
    atcoder = "atcoder"
    gfg = "gfg"


class User(Base):
    __tablename__ = "users"

    # Supabase user UUID (the JWT `sub` claim), stored as text.
    id = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Problem(Base):
    __tablename__ = "problems"
    # A problem is per-user: the same LeetCode URL can exist once per user.
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_problem_user_url"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    official_difficulty = Column(String, nullable=True)  # e.g. "Medium", "1800", "Div2-C"
    tags = Column(String, nullable=True)  # comma-separated, kept simple on purpose
    description_snippet = Column(Text, nullable=True)  # short text used for embeddings
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("Attempt", back_populates="problem", cascade="all, delete-orphan")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5, user's own difficulty rating
    solved_self = Column(Boolean, nullable=False)  # did they solve it without external help
    time_taken_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("Problem", back_populates="attempts")
