"""Unit: digest note (templated, no LLM) + email side-effects. SMTP mocked."""
from unittest.mock import MagicMock

import app.services.digest as digest


def _week(total, solved):
    return {"total": total, "solved_self": solved, "hard_rated": 0,
            "by_platform": {}, "by_tag": {}}


def test_note_empty_week():
    assert "No attempts" in digest.digest_note(_week(0, 0), _week(5, 3), [])


def test_note_flags_progress_and_weak_topic():
    note = digest.digest_note(_week(10, 8), _week(10, 5), [{"tag": "dp", "solved_rate": 0.35}])
    assert "Great progress" in note      # 80% up from 50%
    assert "dp" in note                  # weakest topic surfaced


def test_note_flags_regression():
    note = digest.digest_note(_week(10, 4), _week(10, 8), [])
    assert "slipped" in note


def test_render_lists_due_problems():
    body = digest.render_digest(
        _week(3, 2), [{"title": "Two Sum", "overdue_days": 4, "interval_days": 6}], "note here")
    assert "Two Sum" in body and "4d overdue" in body


def test_send_email_no_op_when_smtp_unconfigured(monkeypatch):
    monkeypatch.setattr(digest.settings, "SMTP_USER", "")
    monkeypatch.setattr(digest.settings, "SMTP_PASSWORD", "")
    # smtplib.SMTP must never be constructed in this path
    monkeypatch.setattr(digest.smtplib, "SMTP",
                        MagicMock(side_effect=AssertionError("SMTP should not be called")))

    digest.send_email("someone@example.com", "subj", "body")  # must not raise


def test_send_email_no_op_when_no_recipient(monkeypatch):
    monkeypatch.setattr(digest.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(digest.settings, "SMTP_PASSWORD", "app-pass")
    monkeypatch.setattr(digest.smtplib, "SMTP",
                        MagicMock(side_effect=AssertionError("SMTP should not be called")))

    digest.send_email("", "subj", "body")  # empty recipient -> skip


def test_send_email_sends_when_configured(monkeypatch):
    server = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = server
    monkeypatch.setattr(digest.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(digest.settings, "SMTP_PASSWORD", "app-pass")
    monkeypatch.setattr(digest.smtplib, "SMTP", lambda host, port: smtp_ctx)

    digest.send_email("you@example.com", "Weekly digest", "great work")

    server.starttls.assert_called_once()
    server.login.assert_called_once_with("me@gmail.com", "app-pass")
    server.send_message.assert_called_once()
