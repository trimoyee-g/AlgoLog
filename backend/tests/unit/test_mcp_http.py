"""Unit: the hosted MCP server's per-request identity and tool wrappers.

No DB and no network: SessionLocal is swapped for a fake session and the tools'
service calls are stubbed, so what's under test is the wiring — who the caller
is, and that each tool asks the service layer the right question. The service
functions themselves are covered by their own tests.

The tools are plain async functions (FastMCP's @mcp.tool() registers and returns
them), so we call them directly with asyncio.run, matching test_mcp_server.py.
"""
import asyncio

import pytest

import app.mcp_http as mcp_http


class _FakeSession:
    def __init__(self, closed):
        self._closed = closed

    def close(self):
        self._closed.append(True)


@pytest.fixture
def db(monkeypatch):
    """A stand-in session; records that the tool closed it."""
    closed = []
    session = _FakeSession(closed)
    monkeypatch.setattr(mcp_http, "SessionLocal", lambda: session)
    session.closed = closed
    return session


def _authenticated_as(monkeypatch, user_id):
    """Fake the contextvar mcp's auth middleware would have populated."""
    class _Token:
        subject = user_id

    monkeypatch.setattr(mcp_http, "get_access_token", lambda: _Token())


# --- SupabaseTokenVerifier ----------------------------------------------------

def _verify(token="jwt-1"):
    return asyncio.run(mcp_http.SupabaseTokenVerifier().verify_token(token))


def test_verify_token_returns_an_access_token_and_upserts_the_user(db, monkeypatch):
    monkeypatch.setattr(mcp_http, "verify_supabase_jwt",
                        lambda t: {"sub": "user-1", "email": "u@example.com"})
    synced = {}
    monkeypatch.setattr(mcp_http, "sync_user",
                        lambda d, uid, email: synced.update(uid=uid, email=email))

    token = _verify("jwt-1")

    assert (token.token, token.client_id, token.subject) == ("jwt-1", "user-1", "user-1")
    assert synced == {"uid": "user-1", "email": "u@example.com"}  # first contact may be via Claude
    assert db.closed  # the session is not leaked


def test_verify_token_rejects_a_bad_jwt_without_leaking_why(monkeypatch):
    def _boom(token):
        raise ValueError("signature has expired and the audience is wrong")

    monkeypatch.setattr(mcp_http, "verify_supabase_jwt", _boom)

    assert _verify() is None


def test_verify_token_rejects_a_jwt_with_no_subject(monkeypatch):
    monkeypatch.setattr(mcp_http, "verify_supabase_jwt", lambda t: {"email": "u@example.com"})

    assert _verify() is None


# --- _caller ------------------------------------------------------------------

def test_caller_is_the_subject_of_this_requests_token(monkeypatch):
    _authenticated_as(monkeypatch, "user-1")

    assert mcp_http._caller() == "user-1"


@pytest.mark.parametrize("token", [None, type("T", (), {"subject": ""})()])
def test_caller_refuses_an_unauthenticated_request(monkeypatch, token):
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: token)

    with pytest.raises(ValueError, match="unauthenticated"):
        mcp_http._caller()


# --- _query -------------------------------------------------------------------

def test_query_runs_off_the_event_loop_and_always_closes_the_session(db):
    assert asyncio.run(mcp_http._query(lambda d: d is db)) is True
    assert db.closed


def test_query_closes_the_session_even_when_the_work_raises(db):
    def _boom(d):
        raise RuntimeError("query blew up")

    with pytest.raises(RuntimeError, match="query blew up"):
        asyncio.run(mcp_http._query(_boom))
    assert db.closed


# --- the three tools ----------------------------------------------------------

def test_get_weak_problems_scopes_to_the_caller_and_passes_filters(db, monkeypatch):
    _authenticated_as(monkeypatch, "user-1")

    class _Problem:
        id, title, url, tags = 7, "Coin Change", "https://lc/coin", "dp"
        platform = type("P", (), {"value": "leetcode"})()

    asked = {}

    def _list_problems(d, user_id, **kwargs):
        asked.update(user_id=user_id, **kwargs)
        return [_Problem()]

    monkeypatch.setattr(mcp_http, "list_problems", _list_problems)

    out = asyncio.run(mcp_http.get_weak_problems(min_rating=5, solved_self=True,
                                                 platform="codeforces"))

    assert asked == {"user_id": "user-1", "min_rating": 5,
                     "solved_self": True, "platform": "codeforces"}
    assert out == [{"id": 7, "title": "Coin Change", "url": "https://lc/coin",
                    "tags": "dp", "platform": "leetcode"}]


def test_get_weak_problems_defaults(db, monkeypatch):
    _authenticated_as(monkeypatch, "user-1")
    asked = {}
    monkeypatch.setattr(mcp_http, "list_problems",
                        lambda d, user_id, **kw: asked.update(kw) or [])

    assert asyncio.run(mcp_http.get_weak_problems()) == []
    assert asked == {"min_rating": 4, "solved_self": False, "platform": None}


def test_get_stats_overview_delegates_to_the_shared_service(db, monkeypatch):
    """Not a second copy of the counting: same overview_stats the REST route serves."""
    _authenticated_as(monkeypatch, "user-1")
    asked = {}
    monkeypatch.setattr(mcp_http, "overview_stats",
                        lambda d, user_id: asked.update(user_id=user_id) or {"total_attempts": 3})

    assert asyncio.run(mcp_http.get_stats_overview()) == {"total_attempts": 3}
    assert asked == {"user_id": "user-1"}


def test_get_recommended_problem_scopes_to_the_caller(db, monkeypatch):
    _authenticated_as(monkeypatch, "user-1")
    asked = {}
    monkeypatch.setattr(mcp_http, "recommend",
                        lambda d, user_id, count: asked.update(user_id=user_id, count=count) or [])

    assert asyncio.run(mcp_http.get_recommended_problem(count=3)) == []
    assert asked == {"user_id": "user-1", "count": 3}


def test_tools_refuse_to_run_unauthenticated(db, monkeypatch):
    """The tenancy guarantee: no caller, no query — never a query with a missing filter."""
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: None)
    monkeypatch.setattr(mcp_http, "list_problems",
                        lambda *a, **k: pytest.fail("queried without an identity"))

    for call in (mcp_http.get_weak_problems(), mcp_http.get_stats_overview(),
                 mcp_http.get_recommended_problem()):
        with pytest.raises(ValueError, match="unauthenticated"):
            asyncio.run(call)
