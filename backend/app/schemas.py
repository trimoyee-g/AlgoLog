from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class AttemptCreate(BaseModel):
    url: str
    title: str
    platform: str  # leetcode | codeforces | codechef | atcoder | gfg
    official_difficulty: Optional[str] = None
    tags: str  # required — the sole embedding signal
    rating: int  # 1-5
    solved_self: bool
    notes: Optional[str] = None


class ProblemUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    platform: Optional[str] = None
    tags: Optional[str] = None
    rating: Optional[int] = None       # updates latest attempt (or creates one)
    solved_self: Optional[bool] = None


class AttemptOut(BaseModel):
    id: int
    rating: int
    solved_self: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProblemOut(BaseModel):
    id: int
    url: str
    title: str
    platform: str
    official_difficulty: Optional[str]
    tags: Optional[str]
    created_at: datetime
    attempts: List[AttemptOut] = []

    class Config:
        from_attributes = True


class SimilarProblemOut(BaseModel):
    id: int
    url: str
    title: str
    platform: str
    tags: Optional[str]
    latest_rating: Optional[int]
    latest_solved_self: Optional[bool]
    similarity: float
