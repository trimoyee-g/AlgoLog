from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.schemas import SimilarProblemOut
from app.services.similarity import similar_problems

router = APIRouter(prefix="/api", tags=["similarity"])


@router.get("/problems/{problem_id}/similar", response_model=list[SimilarProblemOut])
def find_similar(problem_id: int, limit: int = 5, db: Session = Depends(get_db),
                 user_id: str = Depends(require_user)):
    """
    The core 'do I recognize this?' feature. Given a problem, finds the
    closest-embedding problems from history (using pgvector cosine distance)
    so you can surface: 'you struggled with a similar problem before'.
    """
    return similar_problems(db, user_id, problem_id, limit=limit)
