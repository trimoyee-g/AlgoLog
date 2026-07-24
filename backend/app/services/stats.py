"""All-time overview stats for the /api/stats/overview route."""
from sqlalchemy.orm import Session

from app.models import Attempt, Problem


def overview_stats(db: Session, user_id: str) -> dict:
    attempts = db.query(Attempt).filter(Attempt.user_id == user_id)
    total = attempts.count()
    solved_self = attempts.filter(Attempt.solved_self.is_(True)).count()
    return {
        "total_problems": db.query(Problem).filter(Problem.user_id == user_id).count(),
        "total_attempts": total,
        "solved_self_count": solved_self,
        "hard_rated_count": attempts.filter(Attempt.rating >= 4).count(),
        # unaided rate the dashboard shows; guard div-by-zero for a fresh user.
        "unaided_rate": round(solved_self / total, 3) if total else 0.0,
    }
