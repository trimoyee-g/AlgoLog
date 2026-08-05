"""Corrective RAG over the user's uploaded study material.

The loop, and why each stage uses the model it does:

    retrieve  -- bi-encoder + pgvector, k=20. Cheap, high recall, no judgement.
    grade     -- cross-encoder. Scores question and passage *jointly*, which the
                 bi-encoder structurally cannot. This is where bad hits die.
    rewrite   -- chat LLM. Reformulating a question needs generation; there is no
                 encoder trick for it.
    web       -- ddgs. Only when the local corpus turned up nothing at all.
    generate  -- chat LLM, once, over passages that already survived grading.

Note what the chat model is *not* asked to do: score passages one by one. A small
local model is a poor cross-encoder and a slow one — twenty generations to
reproduce a signal a purpose-built reranker gives in one batched CPU call. It is
asked only to decide and to write, which is what generation is actually for.

Degrades in two steps, both silent: with no chat model configured the graph is
retrieve+grade only and the caller (Claude, via the MCP tool) does the writing;
if any LLM call fails the answer comes back None and the passages still return.
"""
import logging
from typing import Literal, TypedDict

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.documents import search_chunks
from app.services.embeddings import rerank
from app.services.llm import chat_model, has_llm

log = logging.getLogger(__name__)

# Tunables. RETRIEVE_K is deliberately far above KEEP_K: grading can throw a
# passage away but can't invent one the search never returned.
RETRIEVE_K = 20
KEEP_K = 5
ENOUGH = 3          # kept passages that count as a complete answer
MAX_ROUNDS = 2      # query rewrites before falling back to the web
MAX_WEB_RESULTS = 5

# Cross-encoder floor. Measured on ms-marco-MiniLM-L-6-v2 with chunk-length text:
#
#   relevant     +6.2 and -7.7      irrelevant   -11.1, -11.3
#   marginal     -10.0              (off-topic but same domain)
#
# So the scale is not centred on zero — a floor of 0 discards good passages and
# sends every query to the web fallback. What the model gets reliably right is the
# *ordering*; the absolute value mostly separates the junk cluster near -11 from
# everything else, which is all this floor is asked to do. KEEP_K does the rest.
#
# ponytail: one absolute floor, no relative-margin rule — revisit if real uploads
# show good passages landing under it. It assumes chunk-length input: on very
# short strings the scale collapses ("memoize the recursion" scores -11.1, same as
# an unrelated recipe), which is why documents.MIN_CHUNK_CHARS exists.
MIN_SCORE = -10.0


class CragState(TypedDict, total=False):
    question: str
    query: str
    user_id: str
    hits: list[dict]
    web: list[dict]
    rounds: int
    regenerated: bool   # the retry budget is spent (set once, never cleared)
    retry: bool         # route back to generate on this pass only
    answer: str | None
    trace: list[str]


class Rewrite(BaseModel):
    query: str = Field(description="A reformulated search query, keywords not prose")


class Grounded(BaseModel):
    grounded: bool = Field(description="True if every claim is supported by the passages")


def _llm(schema):
    return chat_model(0.2).with_structured_output(schema)


def decide_route(n_kept: int, rounds: int, has_llm: bool) -> Literal["generate", "rewrite", "web"]:
    """Pure routing rule — the whole control flow, with no LLM or DB in it.

    Kept separate from the graph so it can be tested directly; every conditional
    edge below is this function.
    """
    if n_kept >= ENOUGH:
        return "generate"
    if not has_llm:
        return "generate"        # can't rewrite without a model; return what we have
    if rounds < MAX_ROUNDS:
        return "rewrite"
    return "web" if n_kept == 0 else "generate"


# --- nodes ---------------------------------------------------------------

def _retrieve(state: CragState, db: Session) -> dict:
    """Vector search, then cross-encoder grading. The two halves of one step."""
    query = state.get("query") or state["question"]
    candidates = search_chunks(db, state["user_id"], query, RETRIEVE_K)
    if not candidates:
        return {"hits": [], "trace": state.get("trace", []) + ["retrieve: corpus empty"]}

    scores = rerank(state["question"], [c["text"] for c in candidates])
    for c, s in zip(candidates, scores):
        c["relevance"] = round(s, 3)

    kept = sorted(
        (c for c in candidates if c["relevance"] >= MIN_SCORE),
        key=lambda c: c["relevance"], reverse=True,
    )[:KEEP_K]
    trace = state.get("trace", []) + [
        f"retrieve({query!r}): {len(candidates)} found, {len(kept)} passed grading"
    ]
    return {"hits": kept, "trace": trace}


def _rewrite(state: CragState) -> dict:
    """Reformulate the query after a thin retrieval, then loop back."""
    rounds = state.get("rounds", 0) + 1
    tried = state.get("query") or state["question"]
    try:
        out = _llm(Rewrite).invoke(
            "Rewrite this into a different search query for a study-notes corpus. "
            "Use distinct keywords and synonyms — the previous query returned too "
            f"little.\n\nOriginal question: {state['question']}\nTried: {tried}"
        )
        query = out.query
    except Exception:
        log.exception("crag: rewrite failed; widening with the raw question")
        query = state["question"]
    return {"query": query, "rounds": rounds,
            "trace": state.get("trace", []) + [f"rewrite -> {query!r}"]}


def _web(state: CragState) -> dict:
    """Last resort: the local corpus has nothing on this."""
    try:
        from ddgs import DDGS

        results = DDGS().text(state["question"], max_results=MAX_WEB_RESULTS)
        web = [{"title": r.get("title", ""), "url": r.get("href", ""),
                "text": r.get("body", "")} for r in results if r.get("href")]
    except Exception:
        log.exception("crag: web fallback failed")
        web = []
    return {"web": web, "trace": state.get("trace", []) + [f"web fallback: {len(web)} results"]}


def _context(state: CragState) -> str:
    parts = [f"[{h['document']} #{h['ordinal']}] {h['text']}" for h in state.get("hits", [])]
    parts += [f"[web: {w['url']}] {w['text']}" for w in state.get("web", [])]
    return "\n\n".join(parts)


def _generate(state: CragState) -> dict:
    """Write the answer from passages that already survived grading."""
    if not has_llm():
        return {"answer": None,
                "trace": state.get("trace", []) + ["generate: skipped (no chat model)"]}
    context = _context(state)
    if not context:
        return {"answer": None, "trace": state.get("trace", []) + ["generate: no context"]}
    try:
        answer = chat_model(0.3).invoke(
            "Answer the question using only the passages below. Be concrete and "
            "specific. If the passages don't cover something, say so rather than "
            f"filling the gap.\n\nQuestion: {state['question']}\n\nPassages:\n{context}"
        ).content
    except Exception:
        log.exception("crag: generation failed; returning passages only")
        return {"answer": None,
                "trace": state.get("trace", []) + ["generate: failed"]}
    return {"answer": answer, "trace": state.get("trace", []) + ["generate: ok"]}


def _check(state: CragState) -> dict:
    """Groundedness gate. One retry maximum, then ship what we have.

    `retry` is the routing signal and `regenerated` is the spent budget — two
    keys, because LangGraph merges partial updates into the state rather than
    replacing it. A single flag meaning both would still be set on the second
    visit and would route back to generate forever.
    """
    if not state.get("answer") or state.get("regenerated") or not has_llm():
        return {"retry": False, "trace": state.get("trace", []) + ["check: skipped"]}
    try:
        out = _llm(Grounded).invoke(
            "Is every claim in the answer supported by the passages?\n\n"
            f"Passages:\n{_context(state)}\n\nAnswer:\n{state['answer']}"
        )
        ok = out.grounded
    except Exception:
        log.exception("crag: groundedness check failed; accepting the answer")
        ok = True
    return {"retry": not ok, "regenerated": True,
            "trace": state.get("trace", []) + [f"check: {'grounded' if ok else 'ungrounded'}"]}


# --- graph ---------------------------------------------------------------

def build_graph(db: Session):
    """Compile the CRAG state machine. `db` is closed over — nodes take state only."""
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(CragState)
    g.add_node("retrieve", lambda s: _retrieve(s, db))
    g.add_node("rewrite", _rewrite)
    # Not "web": LangGraph reserves node names against state keys, and `web` is one.
    g.add_node("web_search", _web)
    g.add_node("generate", _generate)
    g.add_node("check", _check)

    g.add_edge(START, "retrieve")
    g.add_conditional_edges(
        "retrieve",
        lambda s: decide_route(len(s.get("hits", [])), s.get("rounds", 0), has_llm()),
        {"generate": "generate", "rewrite": "rewrite", "web": "web_search"},
    )
    g.add_edge("rewrite", "retrieve")
    g.add_edge("web_search", "generate")
    g.add_edge("generate", "check")
    # One regeneration at most: _check short-circuits to retry=False once
    # regenerated is set, so the second pass through generate exits here.
    g.add_conditional_edges(
        "check",
        lambda s: "generate" if s.get("retry") else END,
        {"generate": "generate", END: END},
    )
    return g.compile()


def ask(db: Session, user_id: str, question: str) -> dict:
    """Run the loop. Always returns passages; `answer` is None when no LLM is configured."""
    final = build_graph(db).invoke(
        {"question": question, "user_id": user_id, "rounds": 0, "trace": []},
        {"recursion_limit": 25},
    )
    return {
        "question": question,
        "answer": final.get("answer"),
        "passages": final.get("hits", []),
        "web": final.get("web", []),
        "trace": final.get("trace", []),
    }


def demo() -> None:
    # Offline self-check: the routing rule is the whole control flow, and it's pure.
    assert decide_route(5, 0, True) == "generate", "plenty of hits -> answer"
    assert decide_route(ENOUGH, 0, True) == "generate", "exactly enough -> answer"
    assert decide_route(1, 0, True) == "rewrite", "thin, rounds left -> rewrite"
    assert decide_route(0, 0, True) == "rewrite", "empty, rounds left -> rewrite"
    assert decide_route(0, MAX_ROUNDS, True) == "web", "empty, rounds spent -> web"
    assert decide_route(1, MAX_ROUNDS, True) == "generate", "thin but non-empty -> ship it"

    # No LLM: never routes anywhere that needs one.
    assert decide_route(0, 0, False) == "generate"
    assert decide_route(1, 0, False) == "generate"

    # The loop must terminate: every rewrite increments rounds, and at MAX_ROUNDS
    # neither branch returns "rewrite".
    assert all(decide_route(n, MAX_ROUNDS, True) != "rewrite" for n in range(ENOUGH))
    print("crag self-check OK")


if __name__ == "__main__":
    demo()
