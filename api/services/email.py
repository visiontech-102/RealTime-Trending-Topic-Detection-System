import asyncio
import logging
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@trending-topics.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def _smtp_configured() -> bool:
    return SMTP_ENABLED and bool(SMTP_HOST)


def _send_smtp_sync(to_email: str, subject: str, body: str) -> None:
    """Blocking SMTP send (invoked via asyncio.to_thread)."""
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if SMTP_USE_TLS:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)

    try:
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
    finally:
        server.quit()


async def _send_email(email: str, subject: str, body: str) -> bool:
    """
    Send email via SMTP when configured, otherwise log to console (dev mode).
    Set SMTP_ENABLED=true and SMTP_HOST in .env for production.
    """
    if _smtp_configured():
        try:
            await asyncio.to_thread(_send_smtp_sync, email, subject, body)
            logger.info("SMTP email sent to %s: %s", email, subject)
            return True
        except Exception as e:
            logger.error("SMTP send failed for %s: %s", email, e)
            return False

    logger.info("=" * 40)
    logger.info("EMAIL (console mode) TO: %s", email)
    logger.info("SUBJECT: %s", subject)
    logger.info("BODY:\n%s", body)
    logger.info("=" * 40)
    print(f"\n{'='*40}\n📧 TO: {email}\n📌 {subject}\n{body}\n{'='*40}\n")
    return True


async def send_2fa_code(email: str, code: str):
    """Sends 2FA verification code."""
    return await _send_email(
        email,
        "Your Two-Factor Authentication Code",
        f"Your verification code is: {code}",
    )


def generate_2fa_code() -> str:
    """Generates a random 6-digit code."""
    return str(random.randint(100000, 999999))


async def send_spike_alert(email: str, spikes: list) -> bool:
    """Alert user when topic trend_score spikes between detection batches."""
    lines = [
        f"• {s['topic_name']}: {s['old_score']:.1f} → {s['new_score']:.1f} (+{s['pct_change']}%)"
        for s in spikes
    ]
    body = (
        "Trending Topic Spike Alert\n\n"
        "The following topics increased significantly since the last detection run:\n\n"
        + "\n".join(lines)
        + "\n\n— Vision Tech Trending Topics System"
    )
    return await _send_email(email, "Trend Spike Alert", body)


async def send_email_digest(email: str, trends: list) -> bool:
    """Daily digest of top detected trends."""
    lines = []
    for i, t in enumerate(trends[:10], 1):
        name = t.get("Name", "Unknown")
        score = t.get("trend_score", 0)
        kw = ", ".join((t.get("Representation") or [])[:5])
        lines.append(f"{i}. {name} (score: {score:.1f}) — {kw}")

    body = (
        "Your Daily Trending Topics Digest\n\n"
        + ("\n".join(lines) if lines else "No trends detected in the latest batch.")
        + "\n\n— Vision Tech Trending Topics System"
    )
    return await _send_email(email, "Daily Trending Topics Digest", body)
