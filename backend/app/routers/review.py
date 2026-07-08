from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.services.recommend import review_queue

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("")
def review_endpoint(
    due_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    user_id: str = Depends(require_user),
):
    """Problems resurfaced by the SM-2 scheduler, soonest-due first.

    due_only=true (default) returns only problems due now; false returns the
    whole schedule so the UI can show 'next up' too.
    """
    return review_queue(db, user_id, due_only=due_only)
