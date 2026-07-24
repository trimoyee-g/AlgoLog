"""Integration: app startup/shutdown.

The other integration tests deliberately construct TestClient *without* the
context manager, so the lifespan never runs. This is the one test that does.

The lifespan no longer touches the schema at all — Alembic owns that now (see
migrations/, and the container's `alembic upgrade head` before boot), because
create_all() can only CREATE and never ALTER, which stops being survivable the
moment other people's data is in the table. So all that's left to assert is the
scheduler.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.main as main

pytestmark = pytest.mark.integration


def test_startup_schedules_the_digest_serves_traffic_and_shuts_down_cleanly(engine):
    """One test, one boot. The lifespan runs `mcp.session_manager.run()` on the manager
    built once at import (main.py), and that manager refuses a second .run() for the
    life of the process — so a second test entering the lifespan cannot pass, no matter
    what it asserts. Production boots once; the suite gets one boot too.
    """
    if engine is None:
        pytest.skip("no Postgres+pgvector test DB (set TEST_DATABASE_URL)")

    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        assert main.scheduler.running
        jobs = main.scheduler.get_jobs()
        assert len(jobs) == 1
        assert str(jobs[0].trigger) == "cron[day_of_week='sun', hour='18', minute='0']"

        # The ANN index is gone for good (migration 0002): it probes a fixed number of
        # lists *before* the user_id filter is applied, so with many users a query can
        # silently come back short. Boot must not quietly put it back.
        with engine.connect() as conn:
            assert conn.execute(text(
                "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_problems_embedding'"
            )).scalar() is None

    assert not main.scheduler.running  # shut down cleanly on exit
