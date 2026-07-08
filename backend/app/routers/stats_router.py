from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.models import Attempt, Problem
from app.services.digest import build_weekly_stats, run_weekly_digest_for_user
from app.services.recommend import recommend, weak_topics

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    total_problems = db.query(Problem).filter(Problem.user_id == user_id).count()
    attempts = db.query(Attempt).filter(Attempt.user_id == user_id)
    total_attempts = attempts.count()
    solved_self = attempts.filter(Attempt.solved_self.is_(True)).count()
    hard = attempts.filter(Attempt.rating >= 4).count()
    return {
        "total_problems": total_problems,
        "total_attempts": total_attempts,
        "solved_self_count": solved_self,
        "hard_rated_count": hard,
    }


@router.get("/weekly")
def weekly(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    return build_weekly_stats(db, user_id)


@router.post("/digest/send-now")
def send_digest_now(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    """Manually trigger your own weekly email digest (normally runs Sunday via APScheduler)."""
    return run_weekly_digest_for_user(db, user_id)


@router.get("/weak-topics")
def get_weak_topics(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    """Tags where your recent solved-unaided rate is below threshold (with enough samples)."""
    return weak_topics(db, user_id)


@router.get("/recommend")
def get_recommend(count: int = 1, db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    """Ranked, reasoned 'what to do next': overdue reviews + weak topics combined."""
    return recommend(db, user_id, count=count)
