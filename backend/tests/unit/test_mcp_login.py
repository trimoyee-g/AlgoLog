"""Unit: the one-time MCP login flow.

The browser is the only thing stubbed out: `webbrowser.open` is replaced by a
function that talks to the real local callback server the way a real browser
would (GET the page, then POST the session back), so the HTTP handler is
exercised end to end. No Supabase, no actual browser.
"""
import json
import socket
import threading
import urllib.request

import pytest

import app.mcp_login as mcp_login


def _free_port() -> int:
    """main() never calls server_close(), so a fresh port per test keeps the
    leaked listening socket of one test from blocking the bind of the next."""
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Fresh module state per test: own token file, own port, own capture buffers.
    monkeypatch (not .clear()) so a test that swaps _done for a stub still restores."""
    monkeypatch.setattr(mcp_login, "TOKEN_FILE", tmp_path / ".algolog" / "mcp_refresh_token")
    monkeypatch.setattr(mcp_login, "CALLBACK_PORT", _free_port())
    monkeypatch.setattr(mcp_login, "_captured", {})
    monkeypatch.setattr(mcp_login, "_done", threading.Event())


def _browser_that_returns(payload):
    """Stands in for the user's browser completing the OAuth redirect."""
    def _open(authorize_url):
        base = f"http://localhost:{mcp_login.CALLBACK_PORT}"
        # the redirect lands on '/', which serves the fragment-reading page...
        page = urllib.request.urlopen(base + "/").read()
        assert b"access_token" in page  # the JS that scrapes location.hash
        # ...whose script then POSTs the parsed fragment back here
        urllib.request.urlopen(urllib.request.Request(
            base + "/token",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )).read()

    return _open


def test_login_saves_the_refresh_token(monkeypatch, capsys):
    monkeypatch.setattr(mcp_login.webbrowser, "open", _browser_that_returns(
        {"access_token": "at-1", "refresh_token": "rt-1", "error": None}))

    mcp_login.main()

    assert mcp_login.TOKEN_FILE.read_text() == "rt-1"
    assert "Saved an MCP-only session" in capsys.readouterr().out


def test_login_surfaces_an_oauth_error(monkeypatch):
    monkeypatch.setattr(mcp_login.webbrowser, "open", _browser_that_returns(
        {"access_token": None, "refresh_token": None, "error": "access_denied"}))

    with pytest.raises(SystemExit, match="Login failed: access_denied"):
        mcp_login.main()

    assert not mcp_login.TOKEN_FILE.exists()


def test_login_without_a_refresh_token_tells_you_to_check_the_redirect_url(monkeypatch):
    monkeypatch.setattr(mcp_login.webbrowser, "open", _browser_that_returns(
        {"access_token": "at-1", "refresh_token": None, "error": None}))

    with pytest.raises(SystemExit, match="didn't return a refresh token"):
        mcp_login.main()

    assert not mcp_login.TOKEN_FILE.exists()


def test_login_times_out_if_the_browser_never_comes_back(monkeypatch):
    class _NeverSet:
        def wait(self, timeout=None):
            return False

    monkeypatch.setattr(mcp_login, "_done", _NeverSet())
    monkeypatch.setattr(mcp_login.webbrowser, "open", lambda url: None)  # user closes the tab

    with pytest.raises(SystemExit, match="Timed out waiting for login"):
        mcp_login.main()


def test_authorize_url_asks_for_github_and_the_local_redirect(monkeypatch):
    opened = {}
    monkeypatch.setattr(mcp_login.webbrowser, "open", lambda url: opened.setdefault("url", url))
    monkeypatch.setattr(mcp_login, "_done", type("E", (), {"wait": lambda self, timeout=None: False})())

    with pytest.raises(SystemExit):
        mcp_login.main()

    assert opened["url"].startswith(f"{mcp_login.SUPABASE_URL}/auth/v1/authorize")
    assert "provider=github" in opened["url"]
    # the redirect target must be percent-encoded, or Supabase truncates it at the '/'
    assert f"redirect_to=http%3A%2F%2Flocalhost%3A{mcp_login.CALLBACK_PORT}%2F" in opened["url"]
