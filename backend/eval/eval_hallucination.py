"""A/B the CRAG loop against plain retrieve-and-generate, on groundedness.

Two question sets, because they measure different failures:

    questions.json     -- answerable. Measures whether the answer stays inside
                          the passages it was given.
    unanswerable.json  -- no coverage in the corpus. Measures whether the model
                          admits that, or invents. This is where hallucination
                          actually lives; the answerable set barely moves.

Baseline and CRAG share the generate prompt and the model (both call
crag._generate), so the only variable is the loop: grading, rewrite, web
fallback, groundedness retry.

    python -m eval.eval_hallucination <user_id>
"""
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.services import crag
from app.services.documents import search_chunks

HERE = Path(__file__).parent


class Verdict(BaseModel):
    grounded: bool = Field(description="True if every claim is supported by the passages")
    abstained: bool = Field(description="True if the answer says the passages don't cover this")


def judge(question: str, context: str, answer: str) -> Verdict:
    return crag._llm(Verdict).invoke(
        "Grade this answer against the passages it was given.\n"
        "grounded: is every factual claim traceable to a passage?\n"
        "abstained: does it state the passages don't cover the question?\n\n"
        f"Question: {question}\n\nPassages:\n{context or '(none)'}\n\nAnswer:\n{answer}"
    )


def run_baseline(db, user_id: str, question: str) -> dict:
    """Top-k vector hits straight to the generate node. No grading, no loop."""
    hits = search_chunks(db, user_id, question, crag.KEEP_K)
    state = {"question": question, "hits": hits}
    return {"answer": crag._generate(state).get("answer"), "passages": hits, "web": []}


def score(db, user_id: str, questions: list[str], runner) -> dict:
    n = grounded = abstained = answered = 0
    for q in questions:
        out = runner(db, user_id, q)
        if not out["answer"]:
            continue                      # no model / no context — not a data point
        n += 1
        v = judge(q, crag._context(out), out["answer"])
        grounded += v.grounded
        abstained += v.abstained
        answered += not v.abstained
        print(f"  {'G' if v.grounded else '.'}{'A' if v.abstained else '.'} {q[:66]}")
    return {"n": n, "grounded": grounded, "abstained": abstained, "answered": answered}


def main(user_id: str) -> None:
    answerable = [q["question"] for q in json.loads((HERE / "questions.json").read_text())]
    unanswerable = json.loads((HERE / "unanswerable.json").read_text())
    systems = {"baseline": run_baseline, "crag": crag.ask}

    db = SessionLocal()
    try:
        results = {}
        for name, runner in systems.items():
            for label, qs in (("answerable", answerable), ("unanswerable", unanswerable)):
                print(f"\n{name} / {label}  (G=grounded, A=abstained)")
                results[name, label] = score(db, user_id, qs, runner)
    finally:
        db.close()

    print(f"\n{'':<10}{'grounded':>22}{'answered anyway':>20}")
    print(f"{'':<10}{'(answerable)':>22}{'(unanswerable)':>20}")
    for name in systems:
        a, u = results[name, "answerable"], results[name, "unanswerable"]
        print(f"{name:<10}{a['grounded']:>13}/{a['n']:<8}{u['answered']:>13}/{u['n']:<8}")
    print("\nLower right = hallucination. That column is the number that matters.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m eval.eval_hallucination <user_id>")
    main(sys.argv[1])
