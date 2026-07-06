import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attempt, Problem, User
from app.services.llm_client import generate


def build_weekly_stats(db: Session, user_id: str) -> dict:
    since = datetime.utcnow() - timedelta(days=7)
    rows = (
        db.query(Attempt, Problem)
        .join(Problem, Attempt.problem_id == Problem.id)
        .filter(Attempt.user_id == user_id)
        .filter(Attempt.created_at >= since)
        .all()
    )
    total = len(rows)
    solved_self = sum(1 for a, _ in rows if a.solved_self)
    hard = sum(1 for a, _ in rows if a.rating >= 4)
    by_platform: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    for a, p in rows:
        by_platform[p.platform.value if hasattr(p.platform, "value") else str(p.platform)] = (
            by_platform.get(p.platform.value if hasattr(p.platform, "value") else str(p.platform), 0) + 1
        )
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


def narrate_digest(stats: dict) -> str:
    if stats["total"] == 0:
        return "No attempts logged this week. Time to get back on the grind!"

    prompt = (
        "You are a terse, encouraging coding-practice coach. Given this weekly stats JSON, "
        "write a 2-3 sentence summary highlighting progress and the weakest area to focus on next week. "
        "Be specific and concrete, no generic fluff.\n\n"
        f"Stats: {stats}"
    )
    return generate(prompt, system="You write short, honest, motivating weekly coding-practice summaries.")


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
    stats = build_weekly_stats(db, user_id)
    narrative = narrate_digest(stats)
    body = f"{narrative}\n\n--- Raw stats ---\n{stats}"
    user = db.get(User, user_id)
    send_email(user.email if user else "", "Your weekly DSA progress digest", body)
    return {"stats": stats, "narrative": narrative}


def run_weekly_digest(db: Session) -> dict:
    """Scheduled job: send each user their own digest."""
    results = []
    for user in db.query(User).all():
        results.append({"user_id": user.id, **run_weekly_digest_for_user(db, user.id)})
    return {"sent": len(results), "results": results}
