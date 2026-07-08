"""Integration: /api/stats overview, weekly breakdown, on-demand digest."""
from datetime import datetime, timedelta

import pytest

from app.models import Problem, Attempt, Platform
from tests.conftest import TEST_USER_ID

pytestmark = pytest.mark.integration


def _seed(db, url, platform, tags, rating, solved, days_ago=0):
    p = Problem(user_id=TEST_USER_ID, url=url, title=url, platform=platform, tags=tags)
    db.add(p)
    db.flush()
    a = Attempt(user_id=TEST_USER_ID, problem_id=p.id, rating=rating, solved_self=solved)
    a.created_at = datetime.utcnow() - timedelta(days=days_ago)
    db.add(a)
    db.commit()
    return p


def test_overview_counts(client, db_session):
    _seed(db_session, "https://1", Platform.leetcode, "dp", rating=5, solved=True)
    _seed(db_session, "https://2", Platform.codeforces, "graphs", rating=2, solved=False)
    _seed(db_session, "https://3", Platform.gfg, "math", rating=4, solved=False)

    body = client.get("/api/stats/overview").json()
    assert body == {"total_problems": 3, "total_attempts": 3,
                    "solved_self_count": 1, "hard_rated_count": 2}  # rating>=4 -> #1 and #3


def test_weekly_breakdown_by_platform_and_tag(client, db_session):
    _seed(db_session, "https://1", Platform.leetcode, "dp,arrays", rating=5, solved=True, days_ago=1)
    _seed(db_session, "https://2", Platform.leetcode, "dp", rating=3, solved=False, days_ago=2)
    _seed(db_session, "https://old", Platform.codeforces, "graphs", rating=4, solved=False, days_ago=30)

    body = client.get("/api/stats/weekly").json()
    assert body["total"] == 2                       # the 30-day-old attempt is excluded
    assert body["by_platform"] == {"leetcode": 2}
    assert body["by_tag"]["dp"] == 2
    assert body["by_tag"]["arrays"] == 1


def test_digest_send_now_returns_stats_note_and_due(client, db_session):
    # SMTP is unconfigured by default, so send_email is a no-op (prints & returns)
    _seed(db_session, "https://1", Platform.leetcode, "dp", rating=5, solved=True)

    body = client.post("/api/stats/digest/send-now").json()
    assert body["stats"]["total"] == 1
    assert isinstance(body["note"], str) and body["note"]
    assert "due" in body  # SM-2 section is part of the digest payload


def test_digest_empty_week_has_default_note(client, db_session):
    body = client.post("/api/stats/digest/send-now").json()
    assert body["stats"]["total"] == 0
    assert "No attempts" in body["note"]
