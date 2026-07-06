from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import attempts, similarity, calibration_router, grading_router, stats_router
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
    # Enable pgvector extension + create tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    # Every Sunday at 6pm, send the digest email
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
app.include_router(similarity.router)
app.include_router(calibration_router.router)
app.include_router(grading_router.router)
app.include_router(stats_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
