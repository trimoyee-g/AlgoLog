from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_user
from app.models import Problem, Attempt, Platform
from app.schemas import AttemptCreate, ProblemOut, ProblemUpdate
from app.services.embeddings import embed_text
from app.services.problems import list_problems

router = APIRouter(prefix="/api", tags=["attempts"])


@router.post("/attempts")
def log_attempt(payload: AttemptCreate, db: Session = Depends(get_db),
                user_id: str = Depends(require_user)):
    """
    Called by the extension every time the user rates a submission.
    Upserts the Problem by (user, URL), then appends a new Attempt row (kept as
    history rather than overwritten, so you can see if your rating changes
    the 2nd/3rd time you meet the same problem).
    """
    
    stmt = pg_insert(Problem).values(
        user_id=user_id,
        url=payload.url,
        title=payload.title,
        platform=Platform(payload.platform),
        tags=payload.tags,
        embedding=embed_text(payload.tags),
    ).on_conflict_do_update(
        constraint="uq_problem_user_url", set_={"url": payload.url},
    ).returning(Problem.id)
    problem_id = db.execute(stmt).scalar_one()

    attempt = Attempt(
        user_id=user_id,
        problem_id=problem_id,
        rating=payload.rating,
        solved_self=payload.solved_self,
        notes=payload.notes,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return {"problem_id": problem_id, "attempt_id": attempt.id}


@router.patch("/problems/{problem_id}", response_model=ProblemOut)
def update_problem(problem_id: int, payload: ProblemUpdate, db: Session = Depends(get_db),
                   user_id: str = Depends(require_user)):
    """Edit a problem's fields. rating/solved_self update the latest attempt
    (or create one if the problem has none yet)."""
    problem = (
        db.query(Problem).options(joinedload(Problem.attempts))
        .filter(Problem.id == problem_id, Problem.user_id == user_id)
        .first()
    )
    if not problem:
        raise HTTPException(404, "Problem not found")

    if payload.url is not None:
        problem.url = payload.url
    if payload.title is not None:
        problem.title = payload.title
    if payload.platform is not None:
        problem.platform = Platform(payload.platform)
    if payload.tags is not None:
        problem.tags = payload.tags

    if payload.tags is not None:
        problem.embedding = embed_text(payload.tags)

    if payload.rating is not None or payload.solved_self is not None:
        latest = max(problem.attempts, key=lambda a: a.created_at) if problem.attempts else None
        if latest is None:
            latest = Attempt(user_id=user_id, problem_id=problem.id, rating=3, solved_self=False)
            db.add(latest)
        if payload.rating is not None:
            latest.rating = payload.rating
        if payload.solved_self is not None:
            latest.solved_self = payload.solved_self

    try:
        db.commit()
    except IntegrityError:  # uq_problem_user_url
        db.rollback()
        raise HTTPException(409, "Another problem already uses that URL")
    db.refresh(problem)
    return problem


@router.delete("/problems/{problem_id}", status_code=204)
def delete_problem(problem_id: int, db: Session = Depends(get_db),
                   user_id: str = Depends(require_user)):
    # One statement: the user filter is the ownership check, attempts go with it
    # via the FK's ON DELETE CASCADE.
    deleted = db.query(Problem).filter(
        Problem.id == problem_id, Problem.user_id == user_id
    ).delete(synchronize_session=False)
    if not deleted:
        raise HTTPException(404, "Problem not found")
    db.commit()


@router.get("/problems", response_model=list[ProblemOut])
def get_problems(
    min_rating: Optional[int] = Query(default=None, ge=1, le=5),
    solved_self: Optional[bool] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user_id: str = Depends(require_user),
):
    """Filterable list, e.g. GET /api/problems?min_rating=4&solved_self=false"""
    return list_problems(
        db, user_id,
        min_rating=min_rating, solved_self=solved_self, platform=platform, tag=tag,
    )
