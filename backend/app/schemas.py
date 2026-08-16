from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models import Platform


class AttemptCreate(BaseModel):
    url: str
    title: str
    platform: Platform  # rejected at the boundary as 422, not deep in the router
    tags: str  # required — the sole embedding signal
    rating: int = Field(ge=1, le=5)
    solved_self: bool
    notes: Optional[str] = None


class ProblemUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    platform: Optional[Platform] = None
    tags: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)  # updates latest attempt (or creates one)
    solved_self: Optional[bool] = None


class AttemptLogged(BaseModel):
    problem_id: int
    attempt_id: int


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
    tags: Optional[str]
    created_at: datetime
    attempts: List[AttemptOut] = []

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    filename: str
    pages: int
    chunks: int
    created_at: datetime

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    question: str


class SimilarProblemOut(BaseModel):
    id: int
    url: str
    title: str
    platform: str
    tags: Optional[str]
    latest_rating: Optional[int]
    latest_solved_self: Optional[bool]
    similarity: float


class OverviewStats(BaseModel):
    total_problems: int
    total_attempts: int
    solved_self_count: int
    hard_rated_count: int
    unaided_rate: float


class WeeklyStats(BaseModel):
    total: int
    solved_self: int
    hard_rated: int
    by_platform: dict[str, int]
    by_tag: dict[str, int]


class WeakTopicOut(BaseModel):
    tag: str
    total_attempts: int
    solved_unaided: int
    solved_rate: float


class ReviewItemOut(BaseModel):
    priority: str
    id: int
    url: str
    title: str
    platform: str
    tags: Optional[str]
    interval_days: int
    ease: float
    repetitions: int
    last_review: datetime
    due: datetime
    overdue_days: int


class RecommendationOut(BaseModel):
    problem_id: int
    problem: str
    url: str
    tags: Optional[str]
    reason: str
    priority: str
    overdue_days: int
    due: datetime


class DigestOut(BaseModel):
    """What send-now returns: the rendered body is emailed, never echoed back."""
    stats: WeeklyStats
    due: List[ReviewItemOut]
    note: str


class DigestPreviewOut(DigestOut):
    body: str  # only the preview hands back the email text


class PassageOut(BaseModel):
    chunk_id: int
    document_id: int
    document: str
    ordinal: int
    text: str
    similarity: float
    relevance: Optional[float] = None  # absent if grading was skipped


class WebResultOut(BaseModel):
    title: str
    url: str
    text: str


class AskResponse(BaseModel):
    question: str
    answer: Optional[str]  # null when no LLM is configured
    passages: List[PassageOut]
    web: List[WebResultOut]
    trace: List[str]
