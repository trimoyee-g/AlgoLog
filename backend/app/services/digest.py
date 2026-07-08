import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attempt, Problem, User
from app.services.recommend import review_queue, weak_topics


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
    user = db.get(User, user_id)
    send_email(user.email if user else "", "Your weekly DSA progress digest", body)
    return {"stats": stats, "due": due, "note": note}


def run_weekly_digest(db: Session) -> dict:
    """Scheduled job: send each user their own digest."""
    results = []
    for user in db.query(User).all():
        results.append({"user_id": user.id, **run_weekly_digest_for_user(db, user.id)})
    return {"sent": len(results), "results": results}
