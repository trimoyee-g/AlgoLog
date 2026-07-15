"""Optional LLM enrichment for the weekly digest.

Best-effort and additive: the deterministic stats, coach note, and review queue
are computed and rendered exactly as before. This layer only *appends* a
personalized paragraph, a few study tips, and a handful of fresh practice
problems found via web search — and only if a local Ollama model is configured
and reachable. Any failure returns None and the digest sends without it, the
same way empty SMTP creds silently disable email.

ponytail: web search is done deterministically (ddgs), the LLM only writes and
curates the real URLs we hand it — a small local model driving an agentic search
loop would hallucinate links. One LLM call, no LangGraph: this is a linear
stats -> search -> write pipeline with no branching or state.
"""
import logging

from pydantic import BaseModel, Field

from app.config import settings

log = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 8


class ProblemSuggestion(BaseModel):
    title: str = Field(description="Problem title, copied from a search result")
    url: str = Field(description="Problem URL, copied verbatim from a search result — never invented")
    why: str = Field(description="One line on why it targets the weak topic")


class Enrichment(BaseModel):
    paragraph: str = Field(description="A short, encouraging, personalized paragraph (2-4 sentences)")
    tips: list[str] = Field(description="4-5 concrete, actionable tips to get a grip on the weak topics")
    problems: list[ProblemSuggestion] = Field(description="4-5 suggested practice problems, chosen only from the provided search results")


def topics_to_target(weak: list[dict], stats: dict) -> list[str]:
    """The weakest tags to coach on; fall back to this week's most-practiced tags."""
    if weak:
        return [w["tag"] for w in weak[:2]]
    by_tag = stats.get("by_tag") or {}
    return sorted(by_tag, key=by_tag.get, reverse=True)[:2]


def _search_problems(topics: list[str]) -> list[dict]:
    from ddgs import DDGS

    query = " ".join(topics) + " practice problems leetcode codeforces"
    results = DDGS().text(query, max_results=MAX_SEARCH_RESULTS)
    return [{"title": r.get("title", ""), "url": r.get("href", ""), "body": r.get("body", "")}
            for r in results if r.get("href")]


def _prompt(stats: dict, topics: list[str], candidates: list[dict]) -> str:
    rate = round(100 * stats["solved_self"] / stats["total"]) if stats["total"] else 0
    listing = "\n".join(f"- {c['title']} | {c['url']} | {c['body'][:160]}" for c in candidates)
    return (
        "You are a supportive competitive-programming coach writing a weekly email.\n"
        f"This week the user logged {stats['total']} attempts and solved {rate}% unaided.\n"
        f"Their weak topics to focus on: {', '.join(topics)}.\n\n"
        "Write an encouraging paragraph, 4-5 concrete tips for gripping those topics, and pick "
        "4-5 practice problems ONLY from the search results below. Copy each url verbatim — never "
        "invent or modify a URL. If a result isn't relevant, skip it.\n\n"
        f"Search results:\n{listing}"
    )


def enrich(stats: dict, weak: list[dict]) -> Enrichment | None:
    """Return LLM enrichment, or None if disabled or anything fails. Never raises."""
    if not settings.OLLAMA_MODEL:
        return None
    topics = topics_to_target(weak, stats)
    if not topics:
        return None
    try:
        from langchain_ollama import ChatOllama

        candidates = _search_problems(topics)
        if not candidates:
            return None
        llm = ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL,
                         temperature=0.3).with_structured_output(Enrichment)
        return llm.invoke(_prompt(stats, topics, candidates))
    except Exception:
        log.exception("digest enrichment failed; sending without it")
        return None


def render_enrichment(e: Enrichment) -> str:
    lines = ["", "--- Coach's corner ---", e.paragraph, "", "Tips:"]
    lines += [f"• {t}" for t in e.tips]
    if e.problems:
        lines += ["", "Fresh problems to try:"]
        lines += [f"• {p.title} — {p.url}\n  {p.why}" for p in e.problems]
    return "\n".join(lines)


def demo() -> None:
    # Offline self-check: no Ollama, no network.
    assert topics_to_target([{"tag": "dp"}, {"tag": "graph"}, {"tag": "math"}], {}) == ["dp", "graph"]
    assert topics_to_target([], {"by_tag": {"greedy": 5, "dp": 9}}) == ["dp", "greedy"]
    assert topics_to_target([], {"by_tag": {}}) == []

    # Disabled (empty model) short-circuits to None without touching network/LLM.
    settings.OLLAMA_MODEL = ""
    assert enrich({"total": 3, "solved_self": 1}, [{"tag": "dp"}]) is None

    rendered = render_enrichment(Enrichment(
        paragraph="Nice week.", tips=["memoize", "draw the recursion tree"],
        problems=[ProblemSuggestion(title="Coin Change", url="http://x/y", why="classic dp")]))
    assert "Coin Change" in rendered and "memoize" in rendered
    print("digest_enrich self-check OK")


if __name__ == "__main__":
    demo()
