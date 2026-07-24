from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.services.digest import build_digest_for_user, build_weekly_stats, run_weekly_digest_for_user
from app.services.recommend import recommend, weak_topics
from app.services.stats import overview_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    return overview_stats(db, user_id)


@router.get("/weekly")
def weekly(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    return build_weekly_stats(db, user_id)


@router.get("/digest/preview")
def preview_digest(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    """Render your weekly digest without emailing it."""
    return build_digest_for_user(db, user_id)


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
