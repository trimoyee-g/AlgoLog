"""Unit: the MCP server's token lifecycle and tool wrappers.

No network and no backend: httpx.AsyncClient is swapped for a fake that records
the request and returns a canned response. The tools are plain async functions
(FastMCP's @tool decorator registers and returns them), so we call them directly
with asyncio.run rather than pulling in an async test plugin.
"""
import asyncio
import time

import pytest

import app.mcp_server as mcp_server


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json


def _fake_client(response, calls):
    """A stand-in for httpx.AsyncClient that records what it was asked to send."""
    class _Client:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, **kwargs):
            calls["post"] = {"url": url, **kwargs}
            return response

        async def get(self, url, **kwargs):
            calls["get"] = {"url": url, **kwargs}
            return response

    return _Client


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Point the token file at a temp dir and reset the cached access token, so
    tests never read/write the real ~/.algolog and never leak state into each other."""
    monkeypatch.setattr(mcp_server, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(mcp_server, "_TOKEN_FILE", tmp_path / ".algolog" / "mcp_refresh_token")
    monkeypatch.setattr(mcp_server, "_access_token", None)
    monkeypatch.setattr(mcp_server, "_access_exp", 0.0)
    monkeypatch.delenv("SUPABASE_REFRESH_TOKEN", raising=False)


# --- refresh-token persistence ------------------------------------------------

def test_load_refresh_token_prefers_the_file_over_the_env_var(monkeypatch):
    mcp_server._save_refresh_token("from-file")
    monkeypatch.setenv("SUPABASE_REFRESH_TOKEN", "from-env")

    assert mcp_server._load_refresh_token() == "from-file"


def test_load_refresh_token_falls_back_to_env_when_no_file(monkeypatch):
    monkeypatch.setenv("SUPABASE_REFRESH_TOKEN", "  from-env  ")
    assert mcp_server._load_refresh_token() == "from-env"


def test_load_refresh_token_is_empty_when_neither_exists():
    assert mcp_server._load_refresh_token() == ""


def test_save_refresh_token_creates_the_parent_dir():
    mcp_server._save_refresh_token("rt-1")

    assert mcp_server._TOKEN_FILE.read_text() == "rt-1"


# --- _refresh -----------------------------------------------------------------

def test_refresh_without_a_session_points_at_mcp_login():
    with pytest.raises(RuntimeError, match="mcp_login"):
        asyncio.run(mcp_server._refresh())


def test_refresh_without_a_supabase_url_says_so(monkeypatch):
    """Fails on the missing setting rather than posting to a URL built from "" ."""
    monkeypatch.setattr(mcp_server, "SUPABASE_URL", "")

    with pytest.raises(RuntimeError, match="Set SUPABASE_URL"):
        asyncio.run(mcp_server._refresh())


def test_refresh_raises_on_a_non_200_from_supabase(monkeypatch):
    mcp_server._save_refresh_token("rt-1")
    monkeypatch.setattr(mcp_server.httpx, "AsyncClient",
                        _fake_client(_FakeResponse(400, text="bad refresh token"), {}))

    with pytest.raises(RuntimeError, match="Token refresh failed \\(400\\)"):
        asyncio.run(mcp_server._refresh())


def test_refresh_caches_the_access_token_and_persists_the_rotated_refresh(monkeypatch):
    mcp_server._save_refresh_token("rt-old")
    calls = {}
    monkeypatch.setattr(mcp_server.httpx, "AsyncClient", _fake_client(
        _FakeResponse(200, {"access_token": "at-1", "expires_at": 9999, "refresh_token": "rt-new"}),
        calls))

    asyncio.run(mcp_server._refresh())

    assert mcp_server._access_token == "at-1"
    assert mcp_server._access_exp == 9999
    assert calls["post"]["url"].endswith("/auth/v1/token")
    assert calls["post"]["params"] == {"grant_type": "refresh_token"}
    assert calls["post"]["json"] == {"refresh_token": "rt-old"}   # sent the old one...
    assert mcp_server._TOKEN_FILE.read_text() == "rt-new"          # ...stored the rotation


def test_refresh_keeps_the_old_token_when_supabase_does_not_rotate(monkeypatch):
    mcp_server._save_refresh_token("rt-old")
    monkeypatch.setattr(mcp_server.httpx, "AsyncClient",
                        _fake_client(_FakeResponse(200, {"access_token": "at-1"}), {}))

    asyncio.run(mcp_server._refresh())

    assert mcp_server._TOKEN_FILE.read_text() == "rt-old"  # no refresh_token in the reply
    assert mcp_server._access_exp == pytest.approx(time.time() + 3600, abs=5)  # default expiry


# --- _access (cache + early refresh) -----------------------------------------

def test_access_reuses_a_still_valid_token(monkeypatch):
    monkeypatch.setattr(mcp_server, "_access_token", "cached")
    monkeypatch.setattr(mcp_server, "_access_exp", time.time() + 600)

    async def _boom():
        raise AssertionError("should not refresh a token that is still good")

    monkeypatch.setattr(mcp_server, "_refresh", _boom)

    assert asyncio.run(mcp_server._access()) == "cached"


def test_access_refreshes_60s_before_expiry(monkeypatch):
    monkeypatch.setattr(mcp_server, "_access_token", "stale")
    monkeypatch.setattr(mcp_server, "_access_exp", time.time() + 30)  # inside the 60s margin

    async def _refresh():
        mcp_server._access_token = "fresh"

    monkeypatch.setattr(mcp_server, "_refresh", _refresh)

    assert asyncio.run(mcp_server._access()) == "fresh"


# --- _get + the three tools ---------------------------------------------------

@pytest.fixture
def sent(monkeypatch):
    """Captures the outbound backend request, with auth already satisfied."""
    async def _access():
        return "at-1"

    monkeypatch.setattr(mcp_server, "_access", _access)
    calls = {}
    monkeypatch.setattr(mcp_server.httpx, "AsyncClient",
                        _fake_client(_FakeResponse(200, text='{"ok": true}'), calls))
    return calls


def test_get_authorizes_and_drops_none_params(sent):
    body = asyncio.run(mcp_server._get("/api/problems", platform=None, min_rating=4))

    assert body == '{"ok": true}'
    assert sent["init"]["headers"] == {"Authorization": "Bearer at-1"}
    assert sent["get"]["url"] == f"{mcp_server.BACKEND_URL}/api/problems"
    assert sent["get"]["params"] == {"min_rating": 4}  # platform=None omitted entirely


def test_get_weak_problems_defaults(sent):
    asyncio.run(mcp_server.get_weak_problems())

    assert sent["get"]["url"].endswith("/api/problems")
    assert sent["get"]["params"] == {"min_rating": 4, "solved_self": "false"}


def test_get_weak_problems_passes_filters_through(sent):
    asyncio.run(mcp_server.get_weak_problems(min_rating=5, solved_self=True, platform="codeforces"))

    assert sent["get"]["params"] == {"min_rating": 5, "solved_self": "true", "platform": "codeforces"}


def test_get_stats_overview(sent):
    asyncio.run(mcp_server.get_stats_overview())

    assert sent["get"]["url"].endswith("/api/stats/overview")


def test_get_recommended_problem(sent):
    asyncio.run(mcp_server.get_recommended_problem(count=3))

    assert sent["get"]["url"].endswith("/api/stats/recommend")
    assert sent["get"]["params"] == {"count": 3}
