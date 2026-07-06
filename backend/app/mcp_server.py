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
from typing import Annotated

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "change-me-to-something-random")

mcp = FastMCP("algolog")


async def _get(path: str, **params) -> str:
    async with httpx.AsyncClient(timeout=30.0, headers={"X-API-Key": API_KEY}) as client:
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


@mcp.tool()
async def predict_difficulty(
    platform: str,
    official_difficulty: str | None = None,
    tags: str | None = None,
) -> str:
    """Predict how hard THIS user will personally find a new problem, based on their trained calibration model."""
    async with httpx.AsyncClient(timeout=30.0, headers={"X-API-Key": API_KEY}) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/calibration/predict",
            json={"platform": platform, "official_difficulty": official_difficulty, "tags": tags},
        )
        return resp.text


if __name__ == "__main__":
    mcp.run()
