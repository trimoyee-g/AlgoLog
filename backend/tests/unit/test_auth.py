"""Unit: JWT verification / user upsert in deps.require_user.

The JWKS network client and jwt.decode are mocked; the db is a stand-in that
records add/commit so we assert the upsert without a real database.
"""
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException

import app.deps as deps


def _fake_db(existing_user=None):
    db = MagicMock()
    db.get.return_value = existing_user
    return db


def test_missing_bearer_prefix_is_401():
    with pytest.raises(HTTPException) as exc:
        deps.require_user(authorization="token-without-bearer", db=_fake_db())
    assert exc.value.status_code == 401


def test_empty_authorization_is_401():
    with pytest.raises(HTTPException) as exc:
        deps.require_user(authorization="", db=_fake_db())
    assert exc.value.status_code == 401


def test_invalid_token_is_401(monkeypatch):
    monkeypatch.setattr(deps._jwks_client, "get_signing_key_from_jwt",
                        lambda t: MagicMock(key="k"))
    monkeypatch.setattr(deps.jwt, "decode",
                        lambda *a, **k: (_ for _ in ()).throw(jwt.InvalidSignatureError("bad")))

    with pytest.raises(HTTPException) as exc:
        deps.require_user(authorization="Bearer tampered", db=_fake_db())
    assert exc.value.status_code == 401


def test_token_without_sub_is_401(monkeypatch):
    monkeypatch.setattr(deps._jwks_client, "get_signing_key_from_jwt",
                        lambda t: MagicMock(key="k"))
    monkeypatch.setattr(deps.jwt, "decode", lambda *a, **k: {"email": "x@y.z"})

    with pytest.raises(HTTPException) as exc:
        deps.require_user(authorization="Bearer good", db=_fake_db())
    assert exc.value.status_code == 401


def test_valid_token_returns_sub_and_creates_user(monkeypatch):
    monkeypatch.setattr(deps._jwks_client, "get_signing_key_from_jwt",
                        lambda t: MagicMock(key="k"))
    monkeypatch.setattr(deps.jwt, "decode",
                        lambda *a, **k: {"sub": "abc-123", "email": "new@user.io"})
    db = _fake_db(existing_user=None)

    uid = deps.require_user(authorization="Bearer good", db=db)

    assert uid == "abc-123"
    db.add.assert_called_once()          # new user row created
    added = db.add.call_args.args[0]
    assert added.id == "abc-123"
    assert added.email == "new@user.io"


def test_unchanged_email_is_not_rewritten(monkeypatch):
    monkeypatch.setattr(deps._jwks_client, "get_signing_key_from_jwt",
                        lambda t: MagicMock(key="k"))
    monkeypatch.setattr(deps.jwt, "decode",
                        lambda *a, **k: {"sub": "abc-123", "email": "same@user.io"})
    db = _fake_db(existing_user=MagicMock(email="same@user.io"))

    assert deps.require_user(authorization="Bearer good", db=db) == "abc-123"

    db.add.assert_not_called()
    db.commit.assert_not_called()  # nothing changed -> no write on every request


def test_existing_user_email_synced_not_duplicated(monkeypatch):
    monkeypatch.setattr(deps._jwks_client, "get_signing_key_from_jwt",
                        lambda t: MagicMock(key="k"))
    monkeypatch.setattr(deps.jwt, "decode",
                        lambda *a, **k: {"sub": "abc-123", "email": "changed@user.io"})
    existing = MagicMock(email="old@user.io")
    db = _fake_db(existing_user=existing)

    uid = deps.require_user(authorization="Bearer good", db=db)

    assert uid == "abc-123"
    db.add.assert_not_called()           # no duplicate insert
    assert existing.email == "changed@user.io"  # email kept in sync
