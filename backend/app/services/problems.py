"""Problem listing + filtering.

Lifted out of the router so the HTTP endpoint and the MCP tool answer
"which problems are giving me trouble" with the same code, rather than two
copies of the latest-attempt rule that drift apart.
"""
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models import Platform, Problem


def list_problems(
    db: Session,
    user_id: str,
    *,
    min_rating: Optional[int] = None,
    solved_self: Optional[bool] = None,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
) -> list[Problem]:
    """Filterable list of one user's problems.

    min_rating / solved_self filter on the *latest* attempt: a problem you
    struggled with a year ago but breezed through last week isn't weak any more.
    """
    q = db.query(Problem).options(joinedload(Problem.attempts)).filter(Problem.user_id == user_id)
    if platform:
        q = q.filter(Problem.platform == Platform(platform))
    if tag:
        q = q.filter(Problem.tags.ilike(f"%{tag}%"))

    problems = q.all()
    if min_rating is None and solved_self is None:
        return problems

    def latest_matches(p: Problem) -> bool:
        if not p.attempts:
            return False
        latest = max(p.attempts, key=lambda a: a.created_at)
        if min_rating is not None and latest.rating < min_rating:
            return False
        if solved_self is not None and latest.solved_self != solved_self:
            return False
        return True

    return [p for p in problems if latest_matches(p)]
