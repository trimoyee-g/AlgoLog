from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.deps import require_user
from app.models import Problem, Attempt
from app.schemas import SimilarProblemOut

router = APIRouter(prefix="/api", tags=["similarity"])


@router.get("/problems/{problem_id}/similar", response_model=list[SimilarProblemOut])
def find_similar(problem_id: int, limit: int = 5, db: Session = Depends(get_db),
                 user_id: str = Depends(require_user)):
    """
    The core 'do I recognize this?' feature. Given a problem, finds the
    closest-embedding problems from history (using pgvector cosine distance)
    so you can surface: 'you struggled with a similar problem before'.
    """
    target = db.query(Problem).filter(
        Problem.id == problem_id, Problem.user_id == user_id
    ).first()
    if not target or target.embedding is None:
        return []

    dist = Problem.embedding.cosine_distance(target.embedding)
    results = (
        db.query(Problem, dist.label("distance"))
        .filter(Problem.user_id == user_id)
        .filter(Problem.id != problem_id)
        .filter(Problem.embedding.isnot(None))
        .order_by(dist)
        .limit(limit)
        .all()
    )

    out = []
    for p, distance in results:
        latest = max(p.attempts, key=lambda a: a.created_at) if p.attempts else None
        # cosine_distance = 1 - cosine_similarity, so convert back for a friendlier number
        similarity = 1 - float(distance) if distance is not None else 0.0
        out.append(SimilarProblemOut(
            id=p.id,
            url=p.url,
            title=p.title,
            platform=p.platform.value if hasattr(p.platform, "value") else str(p.platform),
            tags=p.tags,
            latest_rating=latest.rating if latest else None,
            latest_solved_self=latest.solved_self if latest else None,
            similarity=round(similarity, 3),
        ))
    return out
