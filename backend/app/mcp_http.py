"""AlgoLog MCP server — hosted (Streamable HTTP), mounted into the FastAPI app.

The multi-user counterpart to mcp_server.py. The difference is not the transport,
it's who owns the session:

  stdio (mcp_server.py)  one process per user, on their machine. It holds *its own*
                         Supabase refresh token (mcp_login.py), caches an access
                         token in a module global, and acts as whoever ran it.
                         Correct — because the process *is* one user.

  hosted (this file)     one process, every user. The MCP *client* (Claude) owns the
                         OAuth session and sends the user's JWT on every request;
                         the server holds no token of its own and stores nothing.

That distinction is the whole point. A hosted server with mcp_server.py's design —
one module-global access token, one refresh token on disk — would serve whichever
user refreshed last to everybody. Here identity is per-request, so there is no
shared token to leak, and mcp_login.py's refresh-token-rotation problem simply
stops existing: nothing on the server has a token lineage to rotate.

Tools call the service layer directly rather than looping back over HTTP to our own
API — same code, same tenancy filters, one less hop, no token to relay.

Streamable HTTP, not SSE: SSE is the superseded transport. Don't build it.
"""
import anyio
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from app.config import settings
from app.database import SessionLocal
from app.deps import sync_user, verify_supabase_jwt
from app.models import Attempt, Problem
from app.services.problems import list_problems
from app.services.recommend import recommend


class SupabaseTokenVerifier(TokenVerifier):
    """Verifies the caller's Supabase JWT — the same token, JWKS, and rules as
    require_user. One definition of "a valid AlgoLog identity", two transports."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = verify_supabase_jwt(token)
        except Exception:
            return None  # any bad token is a 401; never leak the reason to the caller

        user_id = payload.get("sub")
        if not user_id:
            return None

        # First contact could be via Claude rather than the dashboard, so the user
        # row may not exist yet. Same upsert require_user does.
        db = SessionLocal()
        try:
            sync_user(db, user_id, payload.get("email", ""))
        finally:
            db.close()

        return AccessToken(token=token, client_id=user_id, subject=user_id, scopes=[])


mcp = FastMCP(
    "algolog",
    token_verifier=SupabaseTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.SUPABASE_PROJECT_URL),   # who mints tokens
        resource_server_url=AnyHttpUrl(settings.MCP_PUBLIC_URL),  # who we are, to the client
        required_scopes=[],
    ),
    stateless_http=True,
)


def _caller() -> str:
    """The user id of whoever's token authenticated *this* request.

    A contextvar, not a global: concurrent users don't see each other's identity.
    This is the line that made the stdio design unsafe to host.
    """
    token = get_access_token()
    if token is None or not token.subject:
        raise ValueError("unauthenticated")
    return token.subject


async def _query(fn):
    """Run a sync SQLAlchemy call off the event loop.

    ponytail: the engine is sync, and blocking the loop would stall every other
    user's request on this replica. Swap for an async engine if the DB ever
    becomes the bottleneck; a thread hop is cheap next to a query.
    """
    def work():
        db = SessionLocal()
        try:
            return fn(db)
        finally:
            db.close()

    return await anyio.to_thread.run_sync(work)


@mcp.tool()
async def get_weak_problems(
    min_rating: int = 4,
    solved_self: bool = False,
    platform: str | None = None,
) -> list[dict]:
    """Problems the user rated difficult (rating >= min_rating) or could not solve unaided."""
    user_id = _caller()
    problems = await _query(lambda db: list_problems(
        db, user_id, min_rating=min_rating, solved_self=solved_self, platform=platform,
    ))
    return [
        {"id": p.id, "title": p.title, "url": p.url, "tags": p.tags,
         "platform": p.platform.value}
        for p in problems
    ]


@mcp.tool()
async def get_stats_overview() -> dict:
    """Overall practice stats: total problems, attempts, solved-unaided, hard-rated."""
    user_id = _caller()

    def stats(db):
        attempts = db.query(Attempt).filter(Attempt.user_id == user_id)
        return {
            "total_problems": db.query(Problem).filter(Problem.user_id == user_id).count(),
            "total_attempts": attempts.count(),
            "solved_self_count": attempts.filter(Attempt.solved_self.is_(True)).count(),
            "hard_rated_count": attempts.filter(Attempt.rating >= 4).count(),
        }

    return await _query(stats)


@mcp.tool()
async def get_recommended_problem(count: int = 1) -> list[dict]:
    """What to work on next. Combines SM-2 spaced-repetition due dates with weak-topic
    detection into a ranked list, each with a 'reason' and a 'priority' (high = overdue
    AND a weak topic). Use it to coach the user unprompted."""
    user_id = _caller()
    return await _query(lambda db: recommend(db, user_id, count=count))
