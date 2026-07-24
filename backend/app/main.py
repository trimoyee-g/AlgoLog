from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.mcp_http import mcp as mcp_server
from app.routers import attempts, review, similarity, stats_router
from app.services.digest import run_weekly_digest

scheduler = BackgroundScheduler()

# Build the MCP ASGI app at import: FastMCP creates its session manager lazily inside
# streamable_http_app(), and `mcp_server.session_manager` raises until it has been called.
mcp_app = mcp_server.streamable_http_app()


def _sunday_digest_job():
    db = SessionLocal()
    try:
        run_weekly_digest(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No DDL here. Schema is owned by Alembic (`alembic upgrade head`, which the
    # container runs before booting) — create_all() can only ever CREATE, never
    # ALTER, so it silently no-ops on a schema change once real users' data exists.

    # Every Sunday at 6pm, send the digest email. Every replica fires this; the
    # digest_sends claim table makes the send itself at-most-once per user/week.
    scheduler.add_job(_sunday_digest_job, "cron", day_of_week="sun", hour=18, minute=0)
    scheduler.start()

    # A mounted sub-app's own lifespan never fires, so the MCP session manager has to
    # be started here or every /mcp request fails with "task group is not initialized".
    async with mcp_server.session_manager.run():
        yield

    scheduler.shutdown()


app = FastAPI(title="AlgoLog", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],  # wildcard + credentials is invalid; pin the frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attempts.router)
app.include_router(review.router)
app.include_router(similarity.router)
app.include_router(stats_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Mounted at the root, and last: routes declared above win, and the OAuth
# protected-resource metadata the MCP client discovers has to live at
# /.well-known/... — mounting under /mcp would bury it a level down where no
# client looks. Serves POST /mcp (Streamable HTTP) plus that metadata document.
app.mount("/", mcp_app)
