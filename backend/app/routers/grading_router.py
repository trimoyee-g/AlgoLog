from fastapi import APIRouter, Depends

from app.deps import require_user
from app.schemas import (
    GradingStartRequest, GradingStartResponse,
    GradingAnswerRequest, GradingAnswerResponse,
)
from app.services import grading_agent

# Stateless LLM grading (in-memory sessions), so just gate access — no per-user data.
router = APIRouter(prefix="/api/grading", tags=["grading"],
                   dependencies=[Depends(require_user)])


@router.post("/start", response_model=GradingStartResponse)
def start(payload: GradingStartRequest):
    session_id, question = grading_agent.start_grading(payload.problem_title, payload.problem_tags)
    return GradingStartResponse(session_id=session_id, question=question)


@router.post("/answer", response_model=GradingAnswerResponse)
def answer(payload: GradingAnswerRequest):
    result = grading_agent.grade_answer(
        session_id=payload.session_id,
        question=payload.question,
        problem_title=payload.problem_title,
        problem_tags=payload.problem_tags,
        user_answer=payload.user_answer,
    )
    return GradingAnswerResponse(**result)
