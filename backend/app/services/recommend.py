"""Reasoning layer: weak-topic detection, SM-2 review queue, and the combined
'what should I do next' recommendation.

Kept here (not in the routers or the MCP server) so the ranking logic lives in
one testable place and both the /stats endpoints and the weekly digest reuse it.
Deterministic on purpose — a coach you can reproduce and debug beats an LLM guess.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import Attempt, Problem
from app.services.scheduler import schedule_for

# Tunables. A tag is "weak" only with enough evidence, and only recent evidence,
# so one bad problem long ago doesn't brand a topic weak forever.
WEAK_THRESHOLD = 0.5      # solved-unaided rate below this = weak
MIN_ATTEMPTS = 3          # ...but only once we've seen at least this many
STRONG_THRESHOLD = 0.8    # for the growth-edge nudge
WINDOW_DAYS = 90          # only count attempts this recent


def split_tags(tags: str | None) -> list[str]:
    return [t.strip() for t in (tags or "").split(",") if t.strip()]


def topic_rates(db: Session, user_id: str, window_days: int = WINDOW_DAYS) -> dict[str, dict]:
    """tag -> {total, solved, rate} across recent attempts on problems with that tag."""
    since = datetime.utcnow() - timedelta(days=window_days)
    rows = (
        db.query(Attempt, Problem)
        .join(Problem, Attempt.problem_id == Problem.id)
        .filter(Attempt.user_id == user_id, Attempt.created_at >= since)
        .all()
    )
    agg: dict[str, list[int]] = {}
    for a, p in rows:
        for t in split_tags(p.tags):
            bucket = agg.setdefault(t, [0, 0])
            bucket[0] += 1
            if a.solved_self:
                bucket[1] += 1
    return {t: {"total": tot, "solved": sol, "rate": sol / tot} for t, (tot, sol) in agg.items()}


def weak_topics(db: Session, user_id: str, *, threshold: float = WEAK_THRESHOLD,
                min_attempts: int = MIN_ATTEMPTS, window_days: int = WINDOW_DAYS) -> list[dict]:
    rates = topic_rates(db, user_id, window_days)
    out = [
        {"tag": t, "total_attempts": r["total"], "solved_unaided": r["solved"],
         "solved_rate": round(r["rate"], 3)}
        for t, r in rates.items()
        if r["total"] >= min_attempts and r["rate"] < threshold
    ]
    out.sort(key=lambda x: x["solved_rate"])
    return out


def review_queue(db: Session, user_id: str, due_only: bool = True) -> list[dict]:
    """SM-2 schedule per problem, soonest-due first (moved here from the router
    so the digest can reuse it)."""
    problems = (
        db.query(Problem).options(joinedload(Problem.attempts))
        .filter(Problem.user_id == user_id).all()
    )
    now = datetime.utcnow()
    out = []
    for p in problems:
        sched = schedule_for(p.attempts)
        if sched is None:
            continue
        if due_only and sched.due > now:
            continue
        out.append({
            "id": p.id,
            "url": p.url,
            "title": p.title,
            "platform": p.platform.value if hasattr(p.platform, "value") else str(p.platform),
            "tags": p.tags,
            "interval_days": sched.interval_days,
            "ease": sched.ease,
            "repetitions": sched.repetitions,
            "last_review": sched.last_review,
            "due": sched.due,
            "overdue_days": max(0, (now - sched.due).days),
        })
    out.sort(key=lambda r: r["due"])
    return out


_RANK = {"high": 3, "medium": 2, "low": 1}


def _tags_meeting(rates: dict[str, dict], threshold: float, *, above: bool) -> set[str]:
    """Tags with enough evidence whose rate is >= threshold (above) or < threshold."""
    return {
        t for t, r in rates.items()
        if r["total"] >= MIN_ATTEMPTS and (r["rate"] >= threshold if above else r["rate"] < threshold)
    }


def rank_candidates(items: list[dict], rates: dict[str, dict], now: datetime, count: int) -> list[dict]:
    """Pure ranking core — no DB, so it's directly testable and deterministic.

    Each item: {problem_id, problem, url, tags, schedule}. Returns the top `count`
    with a reason string + priority:
      high   = overdue AND in a weak topic
      medium = overdue, or in a weak topic (one signal)
      low    = neither: a growth-edge nudge toward a strong topic at a harder tier
    """
    weak = _tags_meeting(rates, WEAK_THRESHOLD, above=False)
    strong = _tags_meeting(rates, STRONG_THRESHOLD, above=True)

    cands = []
    for it in items:
        s = it["schedule"]
        tags = split_tags(it["tags"])
        weak_hit = [t for t in tags if t in weak]
        overdue = s.due <= now
        overdue_days = max(0, (now - s.due).days)

        worst = min(weak_hit, key=lambda t: rates[t]["rate"]) if weak_hit else None
        worst_rate = rates[worst]["rate"] if worst else 1.0

        parts = []
        if overdue:
            days_since = (now - s.last_review).days
            parts.append(f"Due for review (last solved {days_since} days ago, interval {s.interval_days}d)")
        if worst:
            parts.append(f"tagged '{worst}' where you solve only {round(worst_rate * 100)}% unaided")

        if overdue and weak_hit:
            priority = "high"
        elif overdue or weak_hit:
            priority = "medium"
        else:
            priority = "low"
            strong_hit = [t for t in tags if t in strong]
            if strong_hit:
                t = strong_hit[0]
                parts.append(f"you're strong on '{t}' ({round(rates[t]['rate'] * 100)}% unaided) — "
                             f"revisit at a harder tier to push your edge")
            else:
                parts.append("fresh and on track — a light revisit keeps it sharp")

        cands.append({
            "problem_id": it["problem_id"],
            "problem": it["problem"],
            "url": it["url"],
            "tags": it["tags"],
            "reason": " AND ".join(parts),
            "priority": priority,
            "overdue_days": overdue_days,
            "due": s.due,
            "_sort": (-_RANK[priority], -overdue_days, worst_rate),
        })

    cands.sort(key=lambda c: c["_sort"])
    for c in cands:
        del c["_sort"]
    return cands[:count]


def recommend(db: Session, user_id: str, *, count: int = 1) -> list[dict]:
    """Combine 'due for review' (SM-2) with 'weak topic' into a ranked, reasoned list."""
    rates = topic_rates(db, user_id)
    problems = (
        db.query(Problem).options(joinedload(Problem.attempts))
        .filter(Problem.user_id == user_id).all()
    )
    items = []
    for p in problems:
        s = schedule_for(p.attempts)
        if s is None:
            continue
        items.append({"problem_id": p.id, "problem": p.title, "url": p.url,
                      "tags": p.tags, "schedule": s})
    return rank_candidates(items, rates, datetime.utcnow(), count)
