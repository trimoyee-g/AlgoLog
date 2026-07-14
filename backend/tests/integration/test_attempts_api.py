"""Integration: /api/attempts + /api/problems against a real pgvector DB."""
import pytest

from app.models import Problem, Attempt, Platform
from tests.conftest import TEST_USER_ID

pytestmark = pytest.mark.integration


def _payload(**over):
    base = dict(url="https://leetcode.com/two-sum", title="Two Sum",
                platform="leetcode", tags="dp,arrays", rating=4, solved_self=False)
    base.update(over)
    return base


def test_log_attempt_creates_problem_and_attempt(client, db_session):
    r = client.post("/api/attempts", json=_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["problem_id"] and body["attempt_id"]

    assert db_session.query(Problem).count() == 1
    assert db_session.query(Attempt).count() == 1
    p = db_session.query(Problem).one()
    assert p.embedding is not None  # embedding computed from tags on create


def test_repeat_same_url_upserts_problem_appends_attempt(client, db_session):
    client.post("/api/attempts", json=_payload(rating=4))
    client.post("/api/attempts", json=_payload(rating=2))  # same URL, met it again

    assert db_session.query(Problem).count() == 1        # one problem
    assert db_session.query(Attempt).count() == 2        # two attempts kept as history


def test_invalid_platform_is_not_silently_accepted(client):
    # Platform("bogus") raises ValueError inside the handler. This documents the
    # current behavior — ideally the schema would reject it as 422 up front.
    with pytest.raises(ValueError):
        client.post("/api/attempts", json=_payload(platform="bogus"))


def test_update_problem_not_found_is_404(client):
    assert client.patch("/api/problems/9999", json={"title": "x"}).status_code == 404


def test_update_problem_fields_and_reembeds(client, db_session):
    pid = client.post("/api/attempts", json=_payload()).json()["problem_id"]
    before = db_session.get(Problem, pid).embedding

    r = client.patch(f"/api/problems/{pid}", json={"title": "Renamed", "tags": "graphs,bfs"})
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"

    db_session.expire_all()
    p = db_session.get(Problem, pid)
    assert p.tags == "graphs,bfs"
    assert list(p.embedding) != list(before)  # tag change -> re-embedded


def test_update_rating_updates_latest_attempt(client, db_session):
    pid = client.post("/api/attempts", json=_payload(rating=3)).json()["problem_id"]
    client.patch(f"/api/problems/{pid}", json={"rating": 5, "solved_self": True})

    db_session.expire_all()
    latest = db_session.query(Attempt).filter_by(problem_id=pid).one()
    assert latest.rating == 5 and latest.solved_self is True


def test_update_creates_attempt_when_problem_has_none(client, db_session):
    # a problem with zero attempts (seeded directly)
    p = Problem(user_id=TEST_USER_ID, url="https://x/y", title="T",
                platform=Platform.gfg, tags="math")
    db_session.add(p)
    db_session.commit()

    client.patch(f"/api/problems/{p.id}", json={"rating": 2})

    db_session.expire_all()
    attempts = db_session.query(Attempt).filter_by(problem_id=p.id).all()
    assert len(attempts) == 1 and attempts[0].rating == 2


def test_update_url_and_platform(client, db_session):
    pid = client.post("/api/attempts", json=_payload()).json()["problem_id"]

    r = client.patch(f"/api/problems/{pid}",
                     json={"url": "https://codeforces.com/1a", "platform": "codeforces"})
    assert r.status_code == 200

    db_session.expire_all()
    p = db_session.get(Problem, pid)
    assert p.url == "https://codeforces.com/1a"
    assert p.platform == Platform.codeforces


def test_update_solved_self_alone_leaves_rating_untouched(client, db_session):
    pid = client.post("/api/attempts", json=_payload(rating=3, solved_self=False)).json()["problem_id"]

    client.patch(f"/api/problems/{pid}", json={"solved_self": True})

    db_session.expire_all()
    latest = db_session.query(Attempt).filter_by(problem_id=pid).one()
    assert latest.solved_self is True
    assert latest.rating == 3  # not reset by the partial update


def test_update_url_clash_is_409(client, db_session):
    a = client.post("/api/attempts", json=_payload(url="https://a")).json()["problem_id"]
    client.post("/api/attempts", json=_payload(url="https://b"))

    r = client.patch(f"/api/problems/{a}", json={"url": "https://b"})
    assert r.status_code == 409


def test_delete_problem_cascades_attempts(client, db_session):
    pid = client.post("/api/attempts", json=_payload()).json()["problem_id"]

    assert client.delete(f"/api/problems/{pid}").status_code == 204
    assert db_session.query(Problem).count() == 0
    assert db_session.query(Attempt).count() == 0  # attempts cascade-deleted


def test_delete_missing_problem_is_404(client):
    assert client.delete("/api/problems/12345").status_code == 404


def test_list_filters_by_platform_tag_rating_and_solved(client, db_session):
    client.post("/api/attempts", json=_payload(
        url="https://lc/hard", platform="leetcode", tags="dp", rating=5, solved_self=False))
    client.post("/api/attempts", json=_payload(
        url="https://cf/easy", platform="codeforces", tags="greedy", rating=2, solved_self=True))

    assert len(client.get("/api/problems").json()) == 2
    assert len(client.get("/api/problems?platform=leetcode").json()) == 1
    assert len(client.get("/api/problems?tag=greedy").json()) == 1
    assert len(client.get("/api/problems?min_rating=4").json()) == 1
    assert len(client.get("/api/problems?solved_self=true").json()) == 1
    assert len(client.get("/api/problems?min_rating=4&solved_self=true").json()) == 0


def test_list_filters_drop_problems_with_no_attempts(client, db_session):
    # a problem with no attempt log has no rating to compare against, so any
    # rating/solved filter must exclude it rather than crash or let it through
    db_session.add(Problem(user_id=TEST_USER_ID, url="https://x/y", title="T",
                           platform=Platform.gfg, tags="math"))
    db_session.commit()

    assert len(client.get("/api/problems").json()) == 1           # unfiltered: still listed
    assert client.get("/api/problems?min_rating=1").json() == []
    assert client.get("/api/problems?solved_self=false").json() == []


def test_list_min_rating_uses_latest_attempt(client, db_session):
    from datetime import datetime, timedelta
    # first attempt hard, latest attempt easy -> should NOT match min_rating=4
    pid = client.post("/api/attempts", json=_payload(rating=5)).json()["problem_id"]
    client.post("/api/attempts", json=_payload(rating=1))  # same URL, newer + easier

    # pin timestamps so "latest" is unambiguous (avoids same-microsecond ties)
    now = datetime.utcnow()
    hard, easy = db_session.query(Attempt).filter_by(problem_id=pid).order_by(Attempt.rating.desc()).all()
    hard.created_at = now - timedelta(hours=1)
    easy.created_at = now
    db_session.commit()

    assert len(client.get("/api/problems?min_rating=4").json()) == 0
