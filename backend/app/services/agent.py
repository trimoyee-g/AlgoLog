"""A LangGraph ReAct chat agent over the existing service layer.

Same three capabilities the MCP server exposes (weak problems, weak topics,
recommendation), wrapped as LangGraph tools so the dashboard gets a chat agent
("what should I grind this weekend?") without Claude Desktop. Zero new business
logic: the tools just call list_problems / weak_topics / recommend, scoped to the
authenticated user, and JSON-dump the result for the model.

ponytail: this is `create_react_agent` from langgraph.prebuilt — the ReAct loop
is the prebuilt, we don't hand-roll a graph. Heavy imports (langgraph,
langchain_ollama) are lazy so this module loads without them installed, matching
digest_enrich. Runs on the same local Ollama already wired for the digest, so the
model must be tool-capable (e.g. llama3.1).
"""
import json

from sqlalchemy.orm import Session

from app.config import settings

SYSTEM_PROMPT = (
    "You are AlgoLog's practice coach. The user tracks competitive-programming "
    "attempts. Use the tools to ground every claim in their real data — never invent "
    "problems or stats. Be concise and specific; cite the reason/priority the tools give."
)


def _dump(obj) -> str:
    # default=str so datetimes (recommend's due/last_review) serialize cleanly.
    return json.dumps(obj, default=str)


def build_agent(db: Session, user_id: str):
    """Compile a ReAct agent whose tools are bound to this request's db + user."""
    from langchain_core.tools import tool
    from langchain_ollama import ChatOllama
    from langgraph.prebuilt import create_react_agent

    from app.services.problems import list_problems
    from app.services.recommend import recommend, weak_topics

    @tool
    def get_weak_problems(min_rating: int = 4, solved_self: bool = False,
                          platform: str | None = None) -> str:
        """Problems the user rated difficult (rating >= min_rating) or, when solved_self
        is true, only those NOT solved unaided. Optional platform filter
        (leetcode|codeforces|codechef|atcoder|gfg)."""
        problems = list_problems(db, user_id, min_rating=min_rating,
                                 solved_self=solved_self, platform=platform)
        return _dump([{"title": p.title, "url": p.url, "tags": p.tags,
                       "platform": p.platform.value} for p in problems])

    @tool
    def get_weak_topics() -> str:
        """Tags where the user's recent solved-unaided rate is below threshold, with
        enough samples. Each has solved_rate and total_attempts."""
        return _dump(weak_topics(db, user_id))

    @tool
    def get_recommended_problem(count: int = 3) -> str:
        """What to work on next: SM-2 due dates combined with weak topics into a ranked
        list, each with a 'reason' and 'priority' (high = overdue AND a weak topic)."""
        return _dump(recommend(db, user_id, count=count))

    llm = ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL,
                     temperature=0)
    return create_react_agent(
        llm, [get_weak_problems, get_weak_topics, get_recommended_problem],
        prompt=SYSTEM_PROMPT,
    )


def demo() -> None:
    from datetime import datetime
    # The one fragile bit offline: tool outputs must survive JSON (datetimes included).
    out = _dump(recommend_shape := [{"reason": "due", "priority": "high",
                                     "due": datetime(2026, 7, 20)}])
    assert '"due": "2026-07-20 00:00:00"' in out
    assert json.loads(out)[0]["priority"] == "high"
    print("agent self-check OK")


if __name__ == "__main__":
    demo()
