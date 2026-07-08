"""Unit: SM-2 scheduler folds over the attempt log. No DB."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.scheduler import quality_of, schedule_for


def _attempt(rating, solved_self, day):
    return SimpleNamespace(rating=rating, solved_self=solved_self,
                           created_at=datetime(2026, 1, 1) + timedelta(days=day))


def test_quality_mapping():
    assert quality_of(5, solved_self=False) == 2   # unaided fail regardless of rating
    assert quality_of(1, solved_self=True) == 5    # easy pass
    assert quality_of(3, solved_self=True) == 4
    assert quality_of(5, solved_self=True) == 3    # solved but a real struggle


def test_no_attempts_returns_none():
    assert schedule_for([]) is None


def test_passing_streak_grows_interval():
    two = schedule_for([_attempt(1, True, 0), _attempt(1, True, 1)])
    assert two.interval_days == 6          # 1st pass -> 1 day, 2nd -> 6 days
    three = schedule_for([_attempt(1, True, 0), _attempt(1, True, 1), _attempt(1, True, 2)])
    assert three.interval_days > 6         # 3rd+ pass -> interval x ease
    assert three.ease > 2.5                # easy passes push ease up


def test_fail_resets_to_one_day():
    a = [_attempt(1, True, 0), _attempt(1, True, 1), _attempt(4, False, 2)]
    s = schedule_for(a)
    assert s.interval_days == 1
    assert s.repetitions == 0
    assert s.due == a[-1].created_at + timedelta(days=1)


def test_order_independent():
    a = [_attempt(1, True, 0), _attempt(1, True, 1), _attempt(1, True, 2)]
    assert schedule_for(list(reversed(a))).interval_days == schedule_for(a).interval_days
