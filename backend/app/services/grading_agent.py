"""
This mirrors the self-grading loop pattern from SafeHer's LangGraph agents,
hand-rolled here as plain Python (generate -> grade -> retry) so the backend
doesn't need the LangGraph framework as a dependency. Same behavior, one
fewer moving part.

Flow:
  1. User marks an attempt "solved_self = True".
  2. start_grading() asks the local LLM for one probing follow-up question
     about *why* the approach works (not "explain your code").
  3. User answers in the UI.
  4. grade_answer() asks the LLM to grade pass/retry/fail. On "retry" we give
     one follow-up question before giving up (max 2 rounds total).
"""
import uuid

from app.services.llm_client import generate

# In-memory session store is fine for a personal single-user tool.
_SESSIONS: dict[str, dict] = {}
MAX_ROUNDS = 2


def start_grading(problem_title: str, problem_tags: str | None) -> tuple[str, str]:
    session_id = str(uuid.uuid4())
    prompt = (
        f"The user just solved the problem '{problem_title}' "
        f"(tags: {problem_tags or 'unknown'}) and claims they understood it fully. "
        "Ask ONE short, specific follow-up question that tests real understanding of "
        "*why* the approach works (e.g. why this data structure/algorithm applies, "
        "what the time complexity is and why, or an edge case it handles). "
        "Do not ask them to paste their code. Return only the question, no preamble."
    )
    question = generate(prompt, system="You are a strict but fair coding interviewer.")
    _SESSIONS[session_id] = {"round": 1, "problem_title": problem_title, "problem_tags": problem_tags}
    return session_id, question


def grade_answer(session_id: str, question: str, problem_title: str, problem_tags: str | None, user_answer: str) -> dict:
    state = _SESSIONS.get(session_id, {"round": 1})
    prompt = (
        f"Problem: {problem_title} (tags: {problem_tags or 'unknown'})\n"
        f"Question asked: {question}\n"
        f"User's answer: {user_answer}\n\n"
        "Grade this answer for genuine understanding (not just correct terminology). "
        "Respond in exactly this format:\n"
        "VERDICT: pass | retry | fail\n"
        "FEEDBACK: <one sentence>\n"
    )
    raw = generate(prompt, system="You are a strict but fair coding interviewer grading understanding, not just vocabulary.")

    verdict = "retry"
    feedback = raw.strip()
    for line in raw.splitlines():
        if line.upper().startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().lower()
            if v in ("pass", "retry", "fail"):
                verdict = v
        if line.upper().startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()

    follow_up = None
    if verdict == "retry" and state.get("round", 1) < MAX_ROUNDS:
        state["round"] = state.get("round", 1) + 1
        follow_up_prompt = (
            f"The user's answer to '{question}' about problem '{problem_title}' was only partially "
            "correct. Ask one simpler, more targeted follow-up question to give them another chance. "
            "Return only the question."
        )
        follow_up = generate(follow_up_prompt, system="You are a strict but fair coding interviewer.")
        _SESSIONS[session_id] = state
    elif verdict == "retry":
        # ran out of rounds, downgrade to fail rather than looping forever
        verdict = "fail"
        feedback += " (No more follow-up rounds - consider revisiting this problem.)"
        _SESSIONS.pop(session_id, None)
    else:
        _SESSIONS.pop(session_id, None)

    return {"verdict": verdict, "feedback": feedback, "follow_up_question": follow_up}
