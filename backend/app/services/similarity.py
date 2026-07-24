"""Nearest-neighbour problem lookup over pgvector.

Lives here, not in the router, so the query sits with the rest of the service
layer (problems / stats / recommend) rather than inside an HTTP handler.
"""
from sqlalchemy.orm import Session

from app.models import Problem


def similar_problems(db: Session, user_id: str, problem_id: int, limit: int = 5) -> list[dict]:
    """Closest-embedding problems from the user's own history, nearest first.

    Empty when the problem isn't theirs or has no embedding yet.
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
        out.append({
            "id": p.id,
            "url": p.url,
            "title": p.title,
            "platform": p.platform.value if hasattr(p.platform, "value") else str(p.platform),
            "tags": p.tags,
            "latest_rating": latest.rating if latest else None,
            "latest_solved_self": latest.solved_self if latest else None,
            "similarity": round(similarity, 3),
        })
    return out
