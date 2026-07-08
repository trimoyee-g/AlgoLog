"""Spaced-repetition scheduler (SM-2 variant) for problem recall.

We store no scheduler state: interval / ease / repetitions are *derived* by
folding SM-2 over a problem's immutable attempt log. Each Attempt already
carries the two signals we need (`rating` 1-5 own-difficulty, `solved_self`),
so `next_due` is just `last_attempt.created_at + interval_days`.

Quality (SM-2's 0-5) is mapped from the signals AlgoLog already tracks:
    not solved_self            -> 2  (failed recall  -> reset to 1 day)
    solved_self, rating <= 2   -> 5  (easy pass      -> interval stretches)
    solved_self, rating == 3   -> 4
    solved_self, rating >= 4   -> 3  (struggled pass -> interval grows slowly)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_EASE = 1.3
START_EASE = 2.5


def quality_of(rating: int, solved_self: bool) -> int:
    if not solved_self:
        return 2
    if rating <= 2:
        return 5
    if rating == 3:
        return 4
    return 3


@dataclass
class Schedule:
    interval_days: int
    ease: float
    repetitions: int
    last_review: datetime
    due: datetime


def _step(ease: float, interval: int, reps: int, q: int) -> tuple[float, int, int]:
    if q < 3:  # failed / struggled recall -> see it again tomorrow
        return max(MIN_EASE, ease - 0.2), 1, 0
    if reps == 0:
        interval = 1
    elif reps == 1:
        interval = 6
    else:
        interval = round(interval * ease)
    # SM-2 ease update: nail it easily -> ease rises; barely pass -> ease drops.
    ease = max(MIN_EASE, ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    return ease, interval, reps + 1


def schedule_for(attempts) -> Schedule | None:
    """Fold SM-2 over attempts (any order); None if the problem has no attempts."""
    ordered = sorted(attempts, key=lambda a: a.created_at)
    if not ordered:
        return None
    ease, interval, reps = START_EASE, 0, 0
    for a in ordered:
        ease, interval, reps = _step(ease, interval, reps, quality_of(a.rating, a.solved_self))
    last = ordered[-1].created_at
    return Schedule(interval, round(ease, 2), reps, last, last + timedelta(days=interval))
