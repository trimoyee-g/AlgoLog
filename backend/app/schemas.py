from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class AttemptCreate(BaseModel):
    url: str
    title: str
    platform: str  # leetcode | codeforces | codechef | atcoder | gfg
    official_difficulty: Optional[str] = None
    tags: Optional[str] = None
    description_snippet: Optional[str] = None
    rating: int  # 1-5
    solved_self: bool
    time_taken_minutes: Optional[int] = None
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
    time_taken_minutes: Optional[int]
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


class CalibrationRequest(BaseModel):
    platform: str
    official_difficulty: Optional[str] = None
    tags: Optional[str] = None
    time_taken_minutes: Optional[int] = None


class CalibrationResponse(BaseModel):
    predicted_rating: float
    confidence_note: str


class GradingStartRequest(BaseModel):
    problem_title: str
    problem_tags: Optional[str] = None


class GradingStartResponse(BaseModel):
    session_id: str
    question: str


class GradingAnswerRequest(BaseModel):
    session_id: str
    question: str
    problem_title: str
    problem_tags: Optional[str] = None
    user_answer: str


class GradingAnswerResponse(BaseModel):
    verdict: str  # "pass" | "retry" | "fail"
    feedback: str
    follow_up_question: Optional[str] = None
