"""Unit: the corrective-RAG loop.

No DB, no Ollama, no model load — search_chunks, rerank and the LLM calls are all
stubbed, so what's under test is the control flow itself: when the loop rewrites,
when it falls back to the web, and that it always terminates.
"""
import pytest

import app.services.crag as crag
from app.config import settings
from app.services.crag import ENOUGH, MAX_ROUNDS, Grounded, Rewrite, decide_route


@pytest.fixture(autouse=True)
def _no_gemini(monkeypatch):
    """These tests drive the local branch; a real key in .env must not leak in."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")


def _chunk(i: int, text: str) -> dict:
    return {"chunk_id": i, "document_id": 1, "document": "DP Notes",
            "ordinal": i, "text": text, "similarity": 0.9}


@pytest.fixture
def scripted(monkeypatch):
    """Scripted retrieval: each call pops the next batch. Records queries seen."""
    state = {"batches": [], "queries": []}

    def _search(db, user_id, query, k):
        state["queries"].append(query)
        return state["batches"].pop(0) if state["batches"] else []

    monkeypatch.setattr(crag, "search_chunks", _search)
    # Every retrieved passage passes grading; the batches decide what's thin.
    monkeypatch.setattr(crag, "rerank", lambda q, ps: [1.0] * len(ps))
    return state


@pytest.fixture
def llm(monkeypatch):
    """Stub the structured-output LLM used by rewrite and the groundedness check."""
    calls = {"rewrite": 0, "check": 0, "grounded": True}

    class _Stub:
        def __init__(self, schema):
            self.schema = schema

        def invoke(self, prompt):
            if self.schema is Rewrite:
                calls["rewrite"] += 1
                return Rewrite(query=f"rewritten-{calls['rewrite']}")
            calls["check"] += 1
            return Grounded(grounded=calls["grounded"])

    monkeypatch.setattr(crag, "_llm", _Stub)
    return calls


@pytest.fixture
def ollama(monkeypatch):
    """Stub ChatOllama so _generate produces text without a server."""
    import langchain_ollama

    class _Msg:
        content = "Top 3 tips: memoize, define the state, then flip it bottom-up."

    class _Chat:
        def __init__(self, **kwargs):
            pass

        def invoke(self, prompt):
            return _Msg()

    monkeypatch.setattr(langchain_ollama, "ChatOllama", _Chat)


# --- the routing rule ----------------------------------------------------

@pytest.mark.parametrize("kept,rounds,has_llm,expected", [
    (ENOUGH + 2, 0, True, "generate"),      # plenty
    (ENOUGH, 0, True, "generate"),          # exactly enough
    (1, 0, True, "rewrite"),                # thin, budget left
    (0, 0, True, "rewrite"),                # empty, budget left
    (0, MAX_ROUNDS, True, "web"),           # empty, budget spent
    (1, MAX_ROUNDS, True, "generate"),      # thin but non-empty, ship it
    (0, 0, False, "generate"),              # no LLM: can't rewrite
    (1, 0, False, "generate"),
])
def test_decide_route(kept, rounds, has_llm, expected):
    assert decide_route(kept, rounds, has_llm) == expected


def test_route_never_rewrites_once_budget_is_spent():
    """The termination guarantee: rewrite increments rounds, and at the cap no
    branch returns 'rewrite', so retrieve->rewrite->retrieve cannot cycle forever."""
    assert all(decide_route(n, MAX_ROUNDS, True) != "rewrite" for n in range(ENOUGH + 1))


# --- the graph -----------------------------------------------------------

def test_good_retrieval_answers_in_one_pass(monkeypatch, scripted, llm, ollama):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1")
    scripted["batches"] = [[_chunk(i, f"passage {i}") for i in range(ENOUGH)]]

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert len(scripted["queries"]) == 1, "no rewrite needed"
    assert llm["rewrite"] == 0
    assert len(out["passages"]) == ENOUGH
    assert "memoize" in out["answer"]


def test_thin_retrieval_triggers_rewrite_then_succeeds(monkeypatch, scripted, llm, ollama):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1")
    scripted["batches"] = [
        [_chunk(0, "barely related")],                              # thin -> rewrite
        [_chunk(i, f"good {i}") for i in range(ENOUGH)],            # second pass lands
    ]

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert llm["rewrite"] == 1
    assert scripted["queries"] == ["how do I get better at dp?", "rewritten-1"]
    assert len(out["passages"]) == ENOUGH
    assert any("rewrite" in t for t in out["trace"])


def test_empty_corpus_falls_back_to_web(monkeypatch, scripted, llm, ollama):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1")
    scripted["batches"] = []  # every retrieval comes back empty

    hits = [{"title": "DP guide", "href": "https://x/dp", "body": "state and transition"}]
    monkeypatch.setattr("ddgs.DDGS", lambda: type("D", (), {"text": lambda s, q, max_results: hits})())

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert llm["rewrite"] == MAX_ROUNDS, "exhausts rewrites before going to the web"
    assert out["web"] and out["web"][0]["url"] == "https://x/dp"
    assert any("web fallback" in t for t in out["trace"])


def test_no_llm_returns_passages_without_generating(monkeypatch, scripted, llm):
    """The MCP path: no local model, so the loop is retrieve+grade and Claude writes."""
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    scripted["batches"] = [[_chunk(0, "only one passage")]]

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert out["answer"] is None
    assert len(out["passages"]) == 1
    assert llm["rewrite"] == 0, "never rewrites without a model to rewrite with"
    assert len(scripted["queries"]) == 1


def test_ungrounded_answer_is_regenerated_once(monkeypatch, scripted, llm, ollama):
    """The groundedness gate retries exactly once, then ships rather than looping."""
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1")
    llm["grounded"] = False
    scripted["batches"] = [[_chunk(i, f"passage {i}") for i in range(ENOUGH)]]

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert llm["check"] == 1, "the second pass skips the check instead of re-looping"
    assert out["answer"] is not None


def test_grading_discards_low_scoring_passages(monkeypatch, scripted, llm):
    """The cross-encoder, not the vector search, decides what survives.

    Scores are real ms-marco magnitudes: a merely-so-so passage still sits well
    below zero, so the floor has to be down near the junk cluster (see MIN_SCORE).
    """
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    scripted["batches"] = [[_chunk(0, "keep"), _chunk(1, "drop"), _chunk(2, "keep")]]
    monkeypatch.setattr(crag, "rerank",
                        lambda q, ps: [-7.7 if p == "keep" else -11.2 for p in ps])

    out = crag.ask(None, "u1", "anything")

    assert [p["text"] for p in out["passages"]] == ["keep", "keep"]


def test_a_negative_but_relevant_passage_survives(monkeypatch, scripted, llm):
    """Regression: the floor was 0.0, which discarded every real hit and sent
    every question to the web fallback."""
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    scripted["batches"] = [[_chunk(i, f"relevant {i}") for i in range(ENOUGH)]]
    monkeypatch.setattr(crag, "rerank", lambda q, ps: [-7.69] * len(ps))

    out = crag.ask(None, "u1", "how do I get better at dp?")

    assert len(out["passages"]) == ENOUGH
    assert all(p["relevance"] < 0 for p in out["passages"])


def test_passages_come_back_ranked(monkeypatch, scripted, llm):
    """Ordering is the signal the cross-encoder is actually reliable at."""
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    scripted["batches"] = [[_chunk(0, "mid"), _chunk(1, "best"), _chunk(2, "worst")]]
    scores = {"best": 6.2, "mid": -7.7, "worst": -9.9}
    monkeypatch.setattr(crag, "rerank", lambda q, ps: [scores[p] for p in ps])

    out = crag.ask(None, "u1", "anything")

    assert [p["text"] for p in out["passages"]] == ["best", "mid", "worst"]
