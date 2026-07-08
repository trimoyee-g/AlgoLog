"""Unit: the recommendation ranking core. Pure, no DB."""
from datetime import datetime, timedelta

from app.services.recommend import rank_candidates
from app.services.scheduler import Schedule

NOW = datetime(2026, 7, 8)


def _item(pid, tags, *, due_days_ago, interval=6):
    """A candidate whose SM-2 due date is `due_days_ago` days before NOW."""
    due = NOW - timedelta(days=due_days_ago)
    sched = Schedule(interval_days=interval, ease=2.5, repetitions=2,
                     last_review=due - timedelta(days=interval), due=due)
    return {"problem_id": pid, "problem": f"P{pid}", "url": f"u{pid}", "tags": tags, "schedule": sched}


# 'dp' is weak (35%, enough samples); 'greedy' is strong; 'math' too few samples to judge.
RATES = {
    "dp": {"total": 10, "solved": 3, "rate": 0.35},
    "greedy": {"total": 10, "solved": 9, "rate": 0.9},
    "math": {"total": 1, "solved": 0, "rate": 0.0},
}


def test_overdue_and_weak_is_high_with_both_reasons():
    out = rank_candidates([_item(1, "dp", due_days_ago=5)], RATES, NOW, count=1)
    assert out[0]["priority"] == "high"
    assert "Due for review" in out[0]["reason"] and "AND" in out[0]["reason"]
    assert "dp" in out[0]["reason"] and "35%" in out[0]["reason"]


def test_high_outranks_medium():
    items = [
        _item(1, "greedy", due_days_ago=20),   # overdue but strong -> medium
        _item(2, "dp", due_days_ago=1),         # overdue + weak -> high
    ]
    out = rank_candidates(items, RATES, NOW, count=2)
    assert [c["problem_id"] for c in out] == [2, 1]
    assert out[0]["priority"] == "high" and out[1]["priority"] == "medium"


def test_weak_but_not_due_is_medium():
    out = rank_candidates([_item(1, "dp", due_days_ago=-3)], RATES, NOW, count=1)  # due in 3 days
    assert out[0]["priority"] == "medium"
    assert "dp" in out[0]["reason"] and "Due for review" not in out[0]["reason"]


def test_low_sample_topic_not_weak():
    out = rank_candidates([_item(1, "math", due_days_ago=-3)], RATES, NOW, count=1)
    assert out[0]["priority"] == "low"  # 'math' has only 1 attempt -> not flagged weak


def test_growth_edge_nudge_for_strong_fresh_problem():
    out = rank_candidates([_item(1, "greedy", due_days_ago=-10)], RATES, NOW, count=1)
    assert out[0]["priority"] == "low"
    assert "strong on 'greedy'" in out[0]["reason"]


def test_count_limits_results():
    items = [_item(i, "dp", due_days_ago=i) for i in range(1, 6)]
    assert len(rank_candidates(items, RATES, NOW, count=2)) == 2
