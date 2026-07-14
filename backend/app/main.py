from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.routers import attempts, review, similarity, stats_router
from app.services.digest import run_weekly_digest

scheduler = BackgroundScheduler()


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
