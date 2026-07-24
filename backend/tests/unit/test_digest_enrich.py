"""Unit: optional LLM enrichment for the weekly digest.

No Ollama and no network: ddgs and ChatOllama are stubbed. The contract under
test is that enrich() is *never* load-bearing — every failure path returns None
so the digest still sends — plus the prompt's grounding in real search results.
"""
import pytest

import app.services.digest_enrich as de
from app.config import settings
from app.services.digest_enrich import Enrichment, ProblemSuggestion

STATS = {"total": 10, "solved_self": 4, "by_tag": {"dp": 6, "graphs": 3}}
WEAK = [{"tag": "dp"}, {"tag": "graphs"}]


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1")


@pytest.fixture
def hits(monkeypatch):
    """Canned search results; records the query the topics produced."""
    asked = {}
    results = [{"title": "Coin Change", "url": "https://lc/coin", "body": "classic dp"}]

    def _search(topics):
        asked["topics"] = topics
        return results

    monkeypatch.setattr(de, "_search_problems", _search)
    return asked


def _stub_llm(monkeypatch, result):
    """Stand in for ChatOllama(...).with_structured_output(Enrichment)."""
    seen = {}

    class _LLM:
        def __init__(self, **kwargs):
            seen["init"] = kwargs

        def with_structured_output(self, schema):
            seen["schema"] = schema
            return self

        def invoke(self, prompt):
            seen["prompt"] = prompt
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr("langchain_ollama.ChatOllama", _LLM)
    return seen


# --- topics_to_target ---------------------------------------------------------

def test_topics_to_target_prefers_the_two_weakest_tags():
    assert de.topics_to_target([{"tag": "dp"}, {"tag": "graph"}, {"tag": "math"}], {}) == \
        ["dp", "graph"]


def test_topics_to_target_falls_back_to_the_most_practiced_tags():
    assert de.topics_to_target([], {"by_tag": {"greedy": 5, "dp": 9}}) == ["dp", "greedy"]


def test_topics_to_target_falls_back_to_history_on_a_zero_attempt_week():
    """No weak tags and nothing logged this week still leaves a whole history to
    coach on — the quiet week is when the nudge matters most."""
    recent = {"dp": {"rate": 0.71}, "math": {"rate": 1.0}, "greedy": {"rate": 0.4}}
    assert de.topics_to_target([], {"by_tag": {}}, recent) == ["greedy", "dp"]


def test_topics_to_target_is_empty_with_nothing_to_go_on():
    assert de.topics_to_target([], {"by_tag": {}}) == []
    assert de.topics_to_target([], {}) == []  # a fresh user has no by_tag key at all
    assert de.topics_to_target([], {}, {}) == []  # ...and no history either


# --- enrich: the disabled / nothing-to-say paths -------------------------------

def test_enrich_is_none_when_no_model_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    monkeypatch.setattr(de, "_search_problems",
                        lambda t: pytest.fail("searched with enrichment disabled"))

    assert de.enrich(STATS, WEAK) is None


def test_enrich_is_none_when_there_are_no_topics_to_coach(monkeypatch):
    monkeypatch.setattr(de, "_search_problems",
                        lambda t: pytest.fail("searched with no topics"))

    assert de.enrich({"total": 0, "solved_self": 0, "by_tag": {}}, []) is None


def test_enrich_is_none_when_search_finds_nothing(monkeypatch):
    """No results means no real URLs to hand the model — and a model asked to suggest
    problems with no candidates is exactly the one that invents links."""
    monkeypatch.setattr(de, "_search_problems", lambda t: [])
    monkeypatch.setattr("langchain_ollama.ChatOllama",
                        lambda **kw: pytest.fail("called the LLM with no candidates"))

    assert de.enrich(STATS, WEAK) is None


# --- enrich: the happy path ---------------------------------------------------

def test_enrich_returns_the_models_structured_output(hits, monkeypatch):
    expected = Enrichment(paragraph="Nice week.", tips=["memoize"], problems=[])
    seen = _stub_llm(monkeypatch, expected)

    assert de.enrich(STATS, WEAK) is expected
    assert seen["schema"] is Enrichment  # structured output, not free text we'd have to parse
    assert seen["init"]["model"] == "llama3.1"


def test_enrich_grounds_the_prompt_in_the_real_stats_and_search_hits(hits, monkeypatch):
    seen = _stub_llm(monkeypatch, Enrichment(paragraph="p", tips=[], problems=[]))

    de.enrich(STATS, WEAK)

    assert hits["topics"] == ["dp", "graphs"]
    prompt = seen["prompt"]
    assert "10 attempts" in prompt and "40% unaided" in prompt  # 4/10, computed not guessed
    assert "dp, graphs" in prompt
    assert "https://lc/coin" in prompt          # the model copies URLs, never invents them
    assert "never" in prompt and "verbatim" in prompt


def test_enrich_does_not_divide_by_zero_on_an_empty_week(hits, monkeypatch):
    seen = _stub_llm(monkeypatch, Enrichment(paragraph="p", tips=[], problems=[]))

    de.enrich({"total": 0, "solved_self": 0}, WEAK)

    assert "0 attempts" in seen["prompt"] and "0% unaided" in seen["prompt"]


# --- enrich: never load-bearing ----------------------------------------------

def test_enrich_swallows_an_llm_failure_so_the_digest_still_sends(hits, monkeypatch, caplog):
    _stub_llm(monkeypatch, RuntimeError("ollama is down"))

    assert de.enrich(STATS, WEAK) is None
    assert "enrichment failed" in caplog.text  # silent to the user, loud in the logs


def test_enrich_swallows_a_search_failure(monkeypatch):
    def _boom(topics):
        raise RuntimeError("ddgs rate-limited us")

    monkeypatch.setattr(de, "_search_problems", _boom)

    assert de.enrich(STATS, WEAK) is None


def test_enrich_swallows_a_missing_langchain_install(hits, monkeypatch):
    """langchain_ollama is only needed when enrichment is on; an ImportError must
    degrade to a plain digest, not crash Sunday's send."""
    import builtins

    real_import = builtins.__import__

    def _no_langchain(name, *args, **kwargs):
        if name == "langchain_ollama":
            raise ImportError("No module named 'langchain_ollama'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_langchain)

    assert de.enrich(STATS, WEAK) is None


# --- _search_problems ---------------------------------------------------------

def test_search_problems_builds_a_topic_query_and_drops_resultless_rows(monkeypatch):
    seen = {}

    class _DDGS:
        def text(self, query, max_results):
            seen.update(query=query, max_results=max_results)
            return [{"title": "Coin Change", "href": "https://lc/coin", "body": "dp"},
                    {"title": "No link", "body": "dropped"}]  # no href -> unusable

    monkeypatch.setattr("ddgs.DDGS", _DDGS)

    out = de._search_problems(["dp", "graphs"])

    assert seen == {"query": "dp graphs practice problems leetcode codeforces",
                    "max_results": de.MAX_SEARCH_RESULTS}
    assert out == [{"title": "Coin Change", "url": "https://lc/coin", "body": "dp"}]


# --- render_enrichment --------------------------------------------------------

def test_render_enrichment_includes_the_paragraph_tips_and_problems():
    out = de.render_enrichment(Enrichment(
        paragraph="Nice week.", tips=["memoize", "draw the recursion tree"],
        problems=[ProblemSuggestion(title="Coin Change", url="https://lc/coin",
                                    why="classic dp")]))

    assert "Nice week." in out
    assert "• memoize" in out and "• draw the recursion tree" in out
    assert "Coin Change — https://lc/coin" in out and "classic dp" in out


def test_render_enrichment_omits_the_problems_section_when_there_are_none():
    out = de.render_enrichment(Enrichment(paragraph="p", tips=["t"], problems=[]))

    assert "Fresh problems to try:" not in out
    assert "• t" in out


def test_module_self_check_passes(_enabled):
    """`python -m app.services.digest_enrich` is the only check runnable in the image
    (which ships no pytest), so it has to keep working. _enabled's monkeypatch undoes
    demo()'s write to settings.OLLAMA_MODEL."""
    de.demo()
