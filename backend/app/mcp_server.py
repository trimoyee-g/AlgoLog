"""
MCP server for AlgoLog.

Run this and connect it to Claude Desktop / Claude Code, and you can ask
things like "what DP problems did I fail this month" or "log that I just
struggled with this Codeforces problem" directly in chat - Claude calls
these tools against your own backend.

This talks to the FastAPI backend over HTTP rather than the DB directly,
so it stays a thin client and the backend remains the single source of truth.

Run:
    python -m app.mcp_server
Then point Claude Desktop's config at this script (see README for the
claude_desktop_config.json snippet).
"""
import os
import time
import asyncio
from pathlib import Path
from typing import Annotated

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zgeymiyigfcyowdyrdln.supabase.co").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# The MCP server acts as YOU (whoever runs this instance). It authenticates with
# your personal Supabase refresh token and mints short-lived access tokens, exactly
# like the web app / extension do. Supabase ROTATES the refresh token on each use,
# so we persist the latest one to a local file — otherwise it'd break on restart.
# First run seeds from the SUPABASE_REFRESH_TOKEN env var (grab it once from the
# web app's localStorage after logging in).
_TOKEN_FILE = Path.home() / ".algolog" / "mcp_refresh_token"

mcp = FastMCP("algolog")

_lock = asyncio.Lock()
_access_token: str | None = None
_access_exp: float = 0.0


def _load_refresh_token() -> str:
    if _TOKEN_FILE.exists():
        return _TOKEN_FILE.read_text().strip()
    return os.environ.get("SUPABASE_REFRESH_TOKEN", "").strip()


def _save_refresh_token(token: str) -> None:
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(token)


async def _refresh() -> None:
    global _access_token, _access_exp
    refresh_token = _load_refresh_token()
    if not refresh_token:
        raise RuntimeError(
            "No Supabase refresh token. Set SUPABASE_REFRESH_TOKEN once (copy it from "
            "the web app's localStorage after logging in), then this server persists "
            "the rotated tokens itself."
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token",
            params={"grant_type": "refresh_token"},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    _access_token = data["access_token"]
    _access_exp = data.get("expires_at", time.time() + 3600)
    if data.get("refresh_token"):  # rotated — persist for next restart
        _save_refresh_token(data["refresh_token"])


async def _access() -> str:
    async with _lock:
        if not _access_token or time.time() > _access_exp - 60:  # refresh 60s early
            await _refresh()
        return _access_token


async def _get(path: str, **params) -> str:
    token = await _access()
    async with httpx.AsyncClient(timeout=30.0, headers={"Authorization": f"Bearer {token}"}) as client:
        clean = {k: v for k, v in params.items() if v is not None}
        return (await client.get(f"{BACKEND_URL}{path}", params=clean)).text


@mcp.tool()
async def get_weak_problems(
    min_rating: Annotated[int, Field(description="Minimum self-rated difficulty, 1-5")] = 4,
    solved_self: Annotated[bool, Field(description="Filter to only problems NOT solved unaided")] = False,
    platform: Annotated[str | None, Field(description="leetcode | codeforces | codechef | atcoder | gfg")] = None,
) -> str:
    """Get problems the user rated as difficult (rating >= threshold) or could not solve themselves."""
    return await _get(
        "/api/problems",
        min_rating=min_rating,
        solved_self=str(solved_self).lower(),
        platform=platform,
    )


@mcp.tool()
async def get_similar_problems(
    text: Annotated[str, Field(description="Problem title and/or short description")],
    limit: int = 5,
) -> str:
    """Given free-text describing a problem, find similar problems from the user's own history via embedding similarity - useful to check 'have I seen something like this before'."""
    return await _get("/api/problems/search-similar-text", text=text, limit=limit)


@mcp.tool()
async def get_stats_overview() -> str:
    """Get overall practice stats: total problems, total attempts, solved-unaided count, hard-rated count."""
    return await _get("/api/stats/overview")


if __name__ == "__main__":
    mcp.run()
