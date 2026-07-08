"""Unit: Pydantic request schemas — the API's input contract."""
import pytest
from pydantic import ValidationError

from app.schemas import AttemptCreate, ProblemUpdate


def _valid_attempt(**over):
    base = dict(url="https://leetcode.com/x", title="Two Sum",
                platform="leetcode", tags="dp,arrays", rating=3, solved_self=True)
    base.update(over)
    return base


def test_attempt_create_accepts_full_payload():
    a = AttemptCreate(**_valid_attempt(notes="hard"))
    assert a.rating == 3 and a.solved_self is True and a.tags == "dp,arrays"


def test_attempt_create_optional_fields_default_none():
    a = AttemptCreate(**_valid_attempt())
    assert a.official_difficulty is None
    assert a.notes is None


@pytest.mark.parametrize("missing", ["url", "title", "platform", "tags", "rating", "solved_self"])
def test_attempt_create_requires_core_fields(missing):
    payload = _valid_attempt()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        AttemptCreate(**payload)


def test_attempt_create_rating_must_be_int():
    with pytest.raises(ValidationError):
        AttemptCreate(**_valid_attempt(rating="not-a-number"))


def test_problem_update_is_fully_optional():
    assert ProblemUpdate().model_dump(exclude_unset=True) == {}


def test_problem_update_partial():
    u = ProblemUpdate(rating=5)
    dumped = u.model_dump(exclude_unset=True)
    assert dumped == {"rating": 5}  # only set fields surface -> PATCH stays partial
