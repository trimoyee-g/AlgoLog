"""Integration: the two guarantees that only hold against a real Postgres —
digests don't duplicate when several replicas fire the cron, and one bad
recipient doesn't starve every user after it in the loop."""
import pytest

import app.services.digest as digest
from tests.conftest import OTHER_USER_ID, TEST_USER_ID

pytestmark = pytest.mark.integration


class _Sent(list):
    """The recipient list, with the bounce set hung off it — a plain list can't
    carry an attribute, and the tests read both through one fixture value."""
    bounces: set


@pytest.fixture
def sent(monkeypatch):
    """Record recipients instead of sending; a listed address raises like a bounce."""
    recipients, bounces = _Sent(), set()

    def _send(to_email, subject, body):
        if to_email in bounces:
            raise RuntimeError(f"550 mailbox unavailable: {to_email}")
        recipients.append(to_email)

    monkeypatch.setattr(digest, "send_email", _send)
    recipients.bounces = bounces
    return recipients


def test_second_replica_does_not_resend_the_same_week(committing_db, sent):
    first = digest.run_weekly_digest(committing_db)
    second = digest.run_weekly_digest(committing_db)  # the other container's cron

    assert first["sent"] == 2 and second["sent"] == 0
    assert second["skipped"] == 2
    assert sorted(sent) == ["other@example.com", "test@example.com"]  # exactly once each


def test_a_bounced_address_does_not_starve_the_rest_of_the_loop(committing_db, sent):
    sent.bounces.add("test@example.com")

    result = digest.run_weekly_digest(committing_db)

    assert result["failed"] == 1
    assert sent == ["other@example.com"]  # the user after the bounce still got theirs


def test_a_failed_user_is_retried_on_a_rerun(committing_db, sent):
    sent.bounces.add("test@example.com")
    digest.run_weekly_digest(committing_db)

    sent.bounces.clear()  # transient outage cleared; operator reruns the job
    result = digest.run_weekly_digest(committing_db)

    assert result["sent"] == 1 and result["skipped"] == 1
    assert sent == ["other@example.com", "test@example.com"]


def test_claim_is_per_user_per_week(committing_db):
    week = digest.iso_week(digest.datetime.utcnow())

    assert digest.claim_send(committing_db, TEST_USER_ID, week) is True
    assert digest.claim_send(committing_db, TEST_USER_ID, week) is False  # same week: taken
    assert digest.claim_send(committing_db, OTHER_USER_ID, week) is True  # other user: free
    assert digest.claim_send(committing_db, TEST_USER_ID, "2026-W01") is True  # other week: free
