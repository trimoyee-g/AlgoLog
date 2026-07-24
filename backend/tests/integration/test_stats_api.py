"""Integration: /api/stats overview, weekly breakdown, on-demand digest."""
from datetime import datetime, timedelta

import pytest

from app.models import Problem, Attempt, Platform
from app.services.digest import run_weekly_digest
from tests.conftest import TEST_USER_ID, OTHER_USER_ID

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
                    "solved_self_count": 1, "hard_rated_count": 2,  # rating>=4 -> #1 and #3
                    "unaided_rate": 0.333}


def test_overview_unaided_rate_is_zero_for_a_user_with_no_attempts(client):
    assert client.get("/api/stats/overview").json() == {
        "total_problems": 0, "total_attempts": 0, "solved_self_count": 0,
        "hard_rated_count": 0, "unaided_rate": 0.0,  # not a ZeroDivisionError
    }


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


def test_digest_appends_llm_enrichment_to_the_email_when_it_is_available(client, db_session, monkeypatch):
    """The enrichment is additive: it lands in the emailed body, never in the deterministic
    stats/note/due payload the dashboard reads back."""
    from app.services import digest
    from app.services.digest_enrich import Enrichment

    sent = {}
    monkeypatch.setattr(digest, "send_email", lambda to, subj, body: sent.update(body=body))
    monkeypatch.setattr(digest, "enrich", lambda stats, weak: Enrichment(
        paragraph="Strong week on dp.", tips=["memoize"], problems=[]))

    _seed(db_session, "https://1", Platform.leetcode, "dp", rating=5, solved=True)
    body = client.post("/api/stats/digest/send-now").json()

    assert "Coach's corner" in sent["body"] and "Strong week on dp." in sent["body"]
    assert set(body) == {"stats", "due", "note"}


def test_digest_preview_returns_the_rendered_body_without_sending(client, db_session, monkeypatch):
    from app.services import digest

    sent = {}
    monkeypatch.setattr(digest, "send_email", lambda to, subj, body: sent.update(body=body))
    _seed(db_session, "https://1", Platform.leetcode, "dp", rating=5, solved=True)

    body = client.get("/api/stats/digest/preview").json()
    assert body["note"] in body["body"] and "This week" in body["body"]
    assert not sent


def test_weekly_ignores_blank_tags(client, db_session):
    # a stray or trailing comma must not produce an empty "" topic
    _seed(db_session, "https://1", Platform.leetcode, "dp,,arrays,", rating=3, solved=True, days_ago=1)

    by_tag = client.get("/api/stats/weekly").json()["by_tag"]
    assert by_tag == {"dp": 1, "arrays": 1}


def test_scheduled_digest_runs_once_per_user(db_session):
    # the Sunday job fans out over every user; conftest seeds two
    _seed(db_session, "https://1", Platform.leetcode, "dp", rating=5, solved=True)

    out = run_weekly_digest(db_session)

    assert out["sent"] == 2
    by_user = {r["user_id"]: r for r in out["results"]}
    assert by_user[TEST_USER_ID]["stats"]["total"] == 1
    assert by_user[OTHER_USER_ID]["stats"]["total"] == 0  # scoped: doesn't see the other's attempt
    assert "No attempts" in by_user[OTHER_USER_ID]["note"]
