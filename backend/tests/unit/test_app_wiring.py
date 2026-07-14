"""Unit: the two bits of plumbing that aren't exercised by any request —
the get_db dependency's cleanup, and the Sunday digest job's session handling."""
from unittest.mock import MagicMock

import pytest

import app.database as database
import app.main as main


def test_get_db_yields_a_session_and_always_closes_it(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    gen = database.get_db()
    assert next(gen) is session
    session.close.assert_not_called()  # still open while the request runs

    with pytest.raises(StopIteration):
        next(gen)
    session.close.assert_called_once()


def test_sunday_digest_job_runs_the_digest_and_closes_the_session(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(main, "SessionLocal", lambda: session)
    ran_with = {}
    monkeypatch.setattr(main, "run_weekly_digest", lambda db: ran_with.setdefault("db", db))

    main._sunday_digest_job()

    assert ran_with["db"] is session
    session.close.assert_called_once()


def test_sunday_digest_job_closes_the_session_even_if_the_digest_blows_up(monkeypatch):
    # a leaked connection every Sunday would eventually exhaust the pool
    session = MagicMock()
    monkeypatch.setattr(main, "SessionLocal", lambda: session)

    def _boom(db):
        raise RuntimeError("SMTP exploded")

    monkeypatch.setattr(main, "run_weekly_digest", _boom)

    with pytest.raises(RuntimeError):
        main._sunday_digest_job()
    session.close.assert_called_once()
