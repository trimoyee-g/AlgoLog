"""Integration: app startup/shutdown.

The other integration tests deliberately construct TestClient *without* the
context manager, so the lifespan never runs. This is the one test that does run
it, against the test DB (app.main.engine is repointed so startup never touches
the real one).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.main as main

pytestmark = pytest.mark.integration


def test_startup_creates_the_ann_index_and_schedules_the_digest(engine, monkeypatch):
    if engine is None:
        pytest.skip("no Postgres+pgvector test DB (set TEST_DATABASE_URL)")
    monkeypatch.setattr(main, "engine", engine)

    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        with engine.connect() as conn:
            assert conn.execute(text(
                "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_problems_embedding'"
            )).scalar() == 1

        assert main.scheduler.running
        jobs = main.scheduler.get_jobs()
        assert len(jobs) == 1
        assert str(jobs[0].trigger) == "cron[day_of_week='sun', hour='18', minute='0']"

    assert not main.scheduler.running  # shut down cleanly on exit
