"""Integration: the coaching endpoints — /api/review (SM-2 queue),
/api/stats/weak-topics, /api/stats/recommend."""
from datetime import datetime, timedelta

import pytest

from app.models import Problem, Attempt, Platform
from tests.conftest import TEST_USER_ID

pytestmark = pytest.mark.integration


def _problem(db, url, tags, attempts=()):
    """A problem plus its attempt log. Each attempt: (rating, solved_self, days_ago)."""
    p = Problem(user_id=TEST_USER_ID, url=url, title=url, platform=Platform.leetcode, tags=tags)
    db.add(p)
    db.flush()
    for rating, solved, days_ago in attempts:
        a = Attempt(user_id=TEST_USER_ID, problem_id=p.id, rating=rating, solved_self=solved)
        a.created_at = datetime.utcnow() - timedelta(days=days_ago)
        db.add(a)
    db.commit()
    return p


def test_review_returns_only_due_problems_by_default(client, db_session):
    _problem(db_session, "https://overdue", "dp", [(3, True, 5)])   # 1d interval, 5d ago -> due
    _problem(db_session, "https://fresh", "dp", [(3, True, 0)])     # solved today -> due tomorrow
    _problem(db_session, "https://never-tried", "dp")               # no attempts -> no schedule

    due = client.get("/api/review").json()

    assert [r["url"] for r in due] == ["https://overdue"]
    assert due[0]["overdue_days"] == 4
    assert due[0]["interval_days"] == 1


def test_review_due_only_false_returns_the_whole_schedule(client, db_session):
    _problem(db_session, "https://overdue", "dp", [(3, True, 5)])
    _problem(db_session, "https://fresh", "dp", [(3, True, 0)])
    _problem(db_session, "https://never-tried", "dp")  # still excluded: nothing to schedule

    all_scheduled = client.get("/api/review?due_only=false").json()

    assert [r["url"] for r in all_scheduled] == ["https://overdue", "https://fresh"]  # soonest-due first


def test_weak_topics_needs_enough_recent_evidence(client, db_session):
    # dp: 1 of 4 unaided (25%) -> weak.  greedy: only 2 attempts -> not enough to judge.
    _problem(db_session, "https://dp1", "dp", [(5, False, 1), (5, False, 2)])
    _problem(db_session, "https://dp2", "dp", [(4, False, 3), (2, True, 4)])
    _problem(db_session, "https://g1", "greedy", [(5, False, 1), (5, False, 2)])
    # stale evidence outside the 90-day window must not brand a topic weak
    _problem(db_session, "https://old", "trees", [(5, False, 200), (5, False, 201), (5, False, 202)])

    weak = client.get("/api/stats/weak-topics").json()

    assert [w["tag"] for w in weak] == ["dp"]
    assert weak[0] == {"tag": "dp", "total_attempts": 4, "solved_unaided": 1, "solved_rate": 0.25}


def test_recommend_ranks_overdue_weak_problems_first_with_reasons(client, db_session):
    # dp is weak (0/3 unaided); the dp problem is also overdue -> high priority.
    _problem(db_session, "https://dp-overdue", "dp", [(5, False, 9)])
    _problem(db_session, "https://dp-b", "dp", [(5, False, 2)])
    _problem(db_session, "https://dp-c", "dp", [(5, False, 3)])
    _problem(db_session, "https://greedy-fresh", "greedy", [(2, True, 0)])  # not due, not weak
    _problem(db_session, "https://never-tried", "dp")                       # unschedulable

    recs = client.get("/api/stats/recommend?count=5").json()

    assert "https://never-tried" not in [r["url"] for r in recs]
    top = recs[0]
    assert top["url"] == "https://dp-overdue"
    assert top["priority"] == "high"
    assert "Due for review" in top["reason"] and "dp" in top["reason"]
    assert top["overdue_days"] == 8  # 1-day interval after a failed recall
    assert recs[-1]["priority"] == "low"  # the fresh, strong one is last


def test_recommend_count_defaults_to_one(client, db_session):
    _problem(db_session, "https://a", "dp", [(5, False, 9)])
    _problem(db_session, "https://b", "dp", [(5, False, 9)])

    assert len(client.get("/api/stats/recommend").json()) == 1


def test_recommend_is_empty_with_nothing_logged(client, db_session):
    assert client.get("/api/stats/recommend").json() == []
