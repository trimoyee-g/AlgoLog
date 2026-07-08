"""Integration: /api/problems/{id}/similar + free-text search.

Embeddings are set explicitly to orthogonal/one-hot vectors so cosine ordering
is exact and independent of any ML model.
"""
import pytest

from app.models import Problem, Attempt, Platform
from tests.conftest import TEST_USER_ID, OTHER_USER_ID
from tests.helpers import basis_vec, fake_embedding

pytestmark = pytest.mark.integration


def _mk_problem(db, url, tags, embedding, user_id=TEST_USER_ID, rating=None, solved=None):
    p = Problem(user_id=user_id, url=url, title=url, platform=Platform.leetcode,
                tags=tags, embedding=embedding)
    db.add(p)
    db.flush()
    if rating is not None:
        db.add(Attempt(user_id=user_id, problem_id=p.id, rating=rating,
                       solved_self=bool(solved)))
    db.commit()
    return p


def test_similar_returns_empty_when_target_has_no_embedding(client, db_session):
    p = _mk_problem(db_session, "https://x", "dp", embedding=None)
    assert client.get(f"/api/problems/{p.id}/similar").json() == []


def test_similar_orders_by_cosine_distance(client, db_session):
    target = _mk_problem(db_session, "https://target", "dp", basis_vec(0))
    near = _mk_problem(db_session, "https://near", "dp2", basis_vec(0), rating=5, solved=False)  # identical dir
    far = _mk_problem(db_session, "https://far", "graphs", basis_vec(1))                          # orthogonal

    results = client.get(f"/api/problems/{target.id}/similar").json()

    ids = [r["id"] for r in results]
    assert ids == [near.id, far.id]                 # nearest first
    assert results[0]["similarity"] == pytest.approx(1.0)   # identical direction
    assert results[1]["similarity"] == pytest.approx(0.0, abs=1e-6)  # orthogonal
    assert results[0]["latest_rating"] == 5         # latest attempt surfaced


def test_similar_excludes_the_target_itself(client, db_session):
    target = _mk_problem(db_session, "https://t", "dp", basis_vec(0))
    _mk_problem(db_session, "https://o", "dp", basis_vec(0))

    ids = [r["id"] for r in client.get(f"/api/problems/{target.id}/similar").json()]
    assert target.id not in ids


def test_similar_is_scoped_to_the_current_user(client, db_session):
    target = _mk_problem(db_session, "https://mine", "dp", basis_vec(0))
    _mk_problem(db_session, "https://theirs", "dp", basis_vec(0), user_id=OTHER_USER_ID)

    results = client.get(f"/api/problems/{target.id}/similar").json()
    assert results == []  # the other user's identical problem must not leak


def test_similar_respects_limit(client, db_session):
    target = _mk_problem(db_session, "https://t", "dp", basis_vec(0))
    for i in range(1, 6):
        _mk_problem(db_session, f"https://n{i}", "dp", basis_vec(0))

    assert len(client.get(f"/api/problems/{target.id}/similar?limit=2").json()) == 2


def test_search_similar_text_finds_closest_by_tags(client, db_session):
    # store two problems whose embeddings are fake_embedding(their tags);
    # querying the exact tag string of one must rank it first (distance ~0).
    _mk_problem(db_session, "https://a", "dynamic programming", fake_embedding("dynamic programming"))
    _mk_problem(db_session, "https://b", "graphs", fake_embedding("graphs"))

    results = client.get("/api/problems/search-similar-text",
                         params={"text": "dynamic programming"}).json()

    assert results[0]["url"] == "https://a"
    assert results[0]["similarity"] == pytest.approx(1.0, abs=1e-6)
