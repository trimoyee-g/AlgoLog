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
import asyncio
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "change-me-to-something-random")

server = Server("algolog")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_weak_problems",
            description="Get problems the user rated as difficult (rating >= threshold) or could not solve themselves.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_rating": {"type": "integer", "description": "Minimum self-rated difficulty, 1-5", "default": 4},
                    "solved_self": {"type": "boolean", "description": "Filter to only problems NOT solved unaided", "default": False},
                    "platform": {"type": "string", "description": "leetcode | codeforces | codechef | atcoder | gfg"},
                },
            },
        ),
        Tool(
            name="get_similar_problems",
            description="Given free-text describing a problem (title + short description), find similar problems from the user's own history via embedding similarity - useful to check 'have I seen something like this before'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Problem title and/or short description"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="get_stats_overview",
            description="Get overall practice stats: total problems, total attempts, solved-unaided count, hard-rated count.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="predict_difficulty",
            description="Predict how hard THIS user will personally find a new problem, based on their trained calibration model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "official_difficulty": {"type": "string"},
                    "tags": {"type": "string"},
                },
                "required": ["platform"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient(timeout=30.0) as client:
        if name == "get_weak_problems":
            params = {}
            if arguments.get("min_rating") is not None:
                params["min_rating"] = arguments["min_rating"]
            if "solved_self" in arguments:
                params["solved_self"] = str(arguments["solved_self"]).lower()
            if arguments.get("platform"):
                params["platform"] = arguments["platform"]
            resp = await client.get(f"{BACKEND_URL}/api/problems", params=params)
            return [TextContent(type="text", text=resp.text)]

        if name == "get_similar_problems":
            params = {"text": arguments["text"], "limit": arguments.get("limit", 5)}
            resp = await client.get(f"{BACKEND_URL}/api/problems/search-similar-text", params=params)
            return [TextContent(type="text", text=resp.text)]

        if name == "get_stats_overview":
            resp = await client.get(f"{BACKEND_URL}/api/stats/overview")
            return [TextContent(type="text", text=resp.text)]

        if name == "predict_difficulty":
            resp = await client.post(
                f"{BACKEND_URL}/api/calibration/predict",
                json={
                    "platform": arguments["platform"],
                    "official_difficulty": arguments.get("official_difficulty"),
                    "tags": arguments.get("tags"),
                },
            )
            return [TextContent(type="text", text=resp.text)]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
