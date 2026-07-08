"""Shared fixtures.

Unit tests use none of these — they run with no DB, no network.

Integration/E2E tests use `client` + `db_session`, which bind to a real
Postgres+pgvector database (models use pgvector's Vector column and cosine
distance, which SQLite can't emulate). If no test DB is reachable, those
fixtures `pytest.skip`, so `pytest` still passes on a machine with only Python.

  TEST_DATABASE_URL  postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test
"""
import os

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, get_db
from app.deps import require_user
import app.models  # noqa: F401  (register tables on Base.metadata)
from app.models import User

from tests.helpers import fake_embedding

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test",
)
TEST_USER_ID = "user-under-test"
OTHER_USER_ID = "some-other-user"


def _try_make_engine():
    """Return a ready engine, or None if the test DB can't be reached."""
    try:
        eng = create_engine(TEST_DATABASE_URL)
        with eng.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(bind=eng)
        return eng
    except Exception:  # noqa: BLE001 — any connection/driver error means "skip"
        return None


@pytest.fixture(scope="session")
def engine():
    eng = _try_make_engine()
    yield eng
    if eng is not None:
        eng.dispose()


@pytest.fixture
def db_session(engine):
    """Function-scoped session wrapped in a transaction that's rolled back after
    the test, even though the app code under test calls commit() repeatedly.

    Uses the SQLAlchemy "join an external transaction" recipe: app-level commits
    land on a SAVEPOINT that we restart, while the outer transaction is discarded.
    """
    if engine is None:
        pytest.skip("no Postgres+pgvector test DB (set TEST_DATABASE_URL)")

    connection = engine.connect()
    outer = connection.begin()
    session = sessionmaker(bind=connection)()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    # seed both users (require_user is overridden, so its upsert is skipped).
    # OTHER_USER_ID exists so user-scoping tests can insert its rows without an FK error.
    session.add_all([
        User(id=TEST_USER_ID, email="test@example.com"),
        User(id=OTHER_USER_ID, email="other@example.com"),
    ])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _never_send_real_email(monkeypatch):
    """Belt-and-suspenders: no test may hit a real SMTP server, regardless of
    whatever SMTP_* creds happen to live in the ambient .env."""
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")


@pytest.fixture
def client(db_session, monkeypatch):
    """TestClient with the DB + auth dependencies overridden and embeddings faked.

    NOTE: the client is *not* used as a context manager, so the app lifespan
    (real-DB index creation + APScheduler start) never runs — exactly what we want.
    """
    monkeypatch.setattr("app.routers.attempts.embed_text", fake_embedding)

    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_user] = lambda: TEST_USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
