"""Unit: embeddings wrapper. The heavy SentenceTransformer is mocked out."""
from unittest.mock import MagicMock

import numpy as np
import pytest

import app.services.embeddings as emb


@pytest.fixture(autouse=True)
def _clear_model_cache():
    emb._get_model.cache_clear()
    yield
    emb._get_model.cache_clear()


def test_embed_text_returns_plain_list_of_floats(monkeypatch):
    model = MagicMock()
    model.encode.return_value = np.array([0.1, 0.2, 0.3])
    monkeypatch.setattr(emb, "SentenceTransformer", lambda name: model)

    out = emb.embed_text("dp,arrays")

    assert isinstance(out, list)
    assert out == pytest.approx([0.1, 0.2, 0.3])


def test_embed_text_requests_normalized_embeddings(monkeypatch):
    model = MagicMock()
    model.encode.return_value = np.array([1.0, 0.0])
    monkeypatch.setattr(emb, "SentenceTransformer", lambda name: model)

    emb.embed_text("graphs")

    _, kwargs = model.encode.call_args
    assert kwargs.get("normalize_embeddings") is True


def test_model_is_loaded_once_and_cached(monkeypatch):
    calls = {"n": 0}

    def factory(name):
        calls["n"] += 1
        m = MagicMock()
        m.encode.return_value = np.array([0.0])
        return m

    monkeypatch.setattr(emb, "SentenceTransformer", factory)

    emb.embed_text("a")
    emb.embed_text("b")

    assert calls["n"] == 1  # lru_cache(maxsize=1) — model built once
