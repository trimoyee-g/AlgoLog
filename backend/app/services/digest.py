import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attempt, DigestSend, Problem, User
from app.services.digest_enrich import enrich, render_enrichment
from app.services.recommend import review_queue, weak_topics

log = logging.getLogger(__name__)


def _stats_window(db: Session, user_id: str, start: datetime, end: datetime) -> dict:
    rows = (
        db.query(Attempt, Problem)
        .join(Problem, Attempt.problem_id == Problem.id)
        .filter(Attempt.user_id == user_id)
        .filter(Attempt.created_at >= start, Attempt.created_at < end)
        .all()
    )
    total = len(rows)
    solved_self = sum(1 for a, _ in rows if a.solved_self)
    hard = sum(1 for a, _ in rows if a.rating >= 4)
    by_platform: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    for a, p in rows:
        plat = p.platform.value if hasattr(p.platform, "value") else str(p.platform)
        by_platform[plat] = by_platform.get(plat, 0) + 1
        for t in (p.tags or "").split(","):
            t = t.strip()
            if t:
                by_tag[t] = by_tag.get(t, 0) + 1
    return {
        "total": total,
        "solved_self": solved_self,
        "hard_rated": hard,
        "by_platform": by_platform,
        "by_tag": by_tag,
    }


def build_weekly_stats(db: Session, user_id: str) -> dict:
    now = datetime.utcnow()
    return _stats_window(db, user_id, now - timedelta(days=7), now)


def digest_note(this_week: dict, last_week: dict, weak: list[dict]) -> str:
    """The 'coach voice' — templated from simple conditionals, no LLM. Reproducible."""
    if this_week["total"] == 0:
        return "No attempts logged this week — an easy warm-up problem is the best way back in."

    def rate(s: dict) -> float:
        return s["solved_self"] / s["total"] if s["total"] else 0.0

    notes = []
    r_now, r_prev = rate(this_week), rate(last_week)
    if last_week["total"] and r_now > r_prev + 0.05:
        notes.append(f"Great progress — {round(r_now * 100)}% solved unaided, up from {round(r_prev * 100)}% last week.")
    elif last_week["total"] and r_now < r_prev - 0.05:
        notes.append(f"Solved-unaided slipped to {round(r_now * 100)}% from {round(r_prev * 100)}% — worth a steadier week.")
    if weak:
        notes.append(f"Keep an eye on {weak[0]['tag']} ({round(weak[0]['solved_rate'] * 100)}% unaided).")
    return " ".join(notes) or f"Solid week: {this_week['solved_self']}/{this_week['total']} solved unaided."


def render_digest(stats: dict, due: list[dict], note: str) -> str:
    lines = [note, "", "--- This week ---",
             f"Attempts: {stats['total']}  |  Solved unaided: {stats['solved_self']}  |  Hard-rated: {stats['hard_rated']}"]
    if stats["by_tag"]:
        top = sorted(stats["by_tag"].items(), key=lambda kv: -kv[1])[:5]
        lines.append("Topics: " + ", ".join(f"{t} ({n})" for t, n in top))
    lines += ["", "--- Due for review (SM-2) ---"]
    if due:
        for d in due:
            when = f"{d['overdue_days']}d overdue" if d["overdue_days"] else "due today"
            lines.append(f"• {d['title']} — {when} (interval {d['interval_days']}d)")
    else:
        lines.append("Nothing due — you're caught up.")
    return "\n".join(lines)


def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or not to_email:
        print(f"[digest] SMTP not configured or no recipient ({to_email!r}), skipping. Body was:\n", body)
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def run_weekly_digest_for_user(db: Session, user_id: str) -> dict:
    now = datetime.utcnow()
    stats = build_weekly_stats(db, user_id)
    last_week = _stats_window(db, user_id, now - timedelta(days=14), now - timedelta(days=7))
    weak = weak_topics(db, user_id)
    due = review_queue(db, user_id, due_only=True)[:5]
    note = digest_note(stats, last_week, weak)
    body = render_digest(stats, due, note)
    extra = enrich(stats, weak)  # best-effort; None when disabled or on any failure
    if extra:
        body += "\n" + render_enrichment(extra)
    user = db.get(User, user_id)
    send_email(user.email if user else "", "Your weekly DSA progress digest", body)
    return {"stats": stats, "due": due, "note": note}


def iso_week(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def claim_send(db: Session, user_id: str, week: str) -> bool:
    """Insert-or-skip. True means we own this user's send for this week."""
    claimed = db.execute(
        pg_insert(DigestSend)
        .values(user_id=user_id, week=week)
        .on_conflict_do_nothing()
    ).rowcount == 1
    db.commit()
    return claimed


def run_weekly_digest(db: Session) -> dict:
    """Scheduled job: send each user their own digest, at most once per ISO week
    no matter how many replicas fire the cron.

    ponytail: the claim row is the only coordination — no Redis, no leader election.
    If you outgrow the in-process scheduler (SMTP is serial and runs in the web
    process), move the cron to an external trigger hitting a job endpoint; the
    claim stays correct either way.
    """
    week = iso_week(datetime.utcnow())
    results, skipped, failed = [], 0, 0

    # Snapshot the ids, don't iterate ORM instances: the loop commits (and, on
    # failure, rolls back) underneath itself, which expires every live instance —
    # a plain id can't go stale, and this drops a refresh query per user.
    user_ids = [uid for (uid,) in db.query(User.id).all()]

    for user_id in user_ids:
        if not claim_send(db, user_id, week):
            skipped += 1  # another replica already sent this user's digest
            continue
        try:
            results.append({"user_id": user_id, **run_weekly_digest_for_user(db, user_id)})
        except Exception:
            # One bad address must not starve every user after it in the loop.
            # Roll back whatever the failure left half-done, then drop the claim
            # so a rerun this week retries this user.
            failed += 1
            log.exception("weekly digest failed for user %s", user_id)
            db.rollback()
            db.query(DigestSend).filter_by(user_id=user_id, week=week).delete()
            db.commit()

    return {"sent": len(results), "skipped": skipped, "failed": failed, "results": results}
