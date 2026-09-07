"""
Spike alerts and email digests driven by user preferences.
"""
import logging
import os
from datetime import datetime, timezone

from db.connection import get_database
from services.email import send_email_digest, send_spike_alert

logger = logging.getLogger(__name__)

SPIKE_THRESHOLD_PCT = float(os.getenv("SPIKE_THRESHOLD_PCT", "25"))
DIGEST_INTERVAL_HOURS = float(os.getenv("DIGEST_INTERVAL_HOURS", "24"))

# Users who never opened Settings have no preference field. GET /auth/preferences
# reports email digests as on by default, so the recipient query has to agree —
# matching only `True` would silently exclude everyone who never touched a toggle.
DIGEST_RECIPIENT_QUERY = {"email_digests": {"$ne": False}}
SPIKE_RECIPIENT_QUERY = {"spike_alerts": True}  # default is off, so exact match is correct


def _as_naive_utc(value):
    """MongoDB may hand back aware or naive datetimes; normalise for comparison."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


async def _deliver(send_fn, recipients, *args) -> tuple[int, int]:
    """
    Send to each recipient, counting real successes.

    The send helpers return False when SMTP rejects the message; ignoring that
    return value would make `digests_sent` a count of attempts, not deliveries.
    """
    sent = failed = 0
    for user in recipients:
        email = user.get("email")
        if not email:
            continue
        if await send_fn(email, *args):
            sent += 1
        else:
            failed += 1
            logger.warning("Delivery failed for %s via %s", email, send_fn.__name__)
    return sent, failed


async def _get_latest_two_batches(db):
    """Return (current_batch, previous_batch) trend lists by calculated_at."""
    coll = db["detected_trends"]
    pipeline = [
        {"$group": {"_id": "$calculated_at"}},
        {"$sort": {"_id": -1}},
        {"$limit": 2},
    ]
    times = [doc["_id"] async for doc in coll.aggregate(pipeline)]
    if not times:
        return [], []
    current = await coll.find({"calculated_at": times[0]}).to_list(length=200)
    previous = await coll.find({"calculated_at": times[1]}).to_list(length=200) if len(times) > 1 else []
    return current, previous


def _detect_spikes(current: list, previous: list) -> list:
    """Topics whose trend_score rose by >= SPIKE_THRESHOLD_PCT vs previous batch."""
    prev_by_name = {t.get("Name"): t.get("trend_score", 0) for t in previous}
    spikes = []
    for t in current:
        name = t.get("Name")
        score = t.get("trend_score", 0)
        old = prev_by_name.get(name)
        if old and old > 0:
            pct_change = ((score - old) / old) * 100
            if pct_change >= SPIKE_THRESHOLD_PCT:
                spikes.append({
                    "topic_name": name,
                    "old_score": old,
                    "new_score": score,
                    "pct_change": round(pct_change, 1),
                    "keywords": t.get("Representation", [])[:5],
                })
        elif score >= 50 and not old:
            spikes.append({
                "topic_name": name,
                "old_score": 0,
                "new_score": score,
                "pct_change": 100.0,
                "keywords": t.get("Representation", [])[:5],
            })
    return sorted(spikes, key=lambda x: x["pct_change"], reverse=True)


async def check_and_send_spike_alerts() -> dict:
    """Notify users with spike_alerts enabled when scores jump between batches."""
    db = await get_database()
    current, previous = await _get_latest_two_batches(db)
    if not current or not previous:
        return {"status": "skipped", "reason": "insufficient_batches"}

    spikes = _detect_spikes(current, previous)
    if not spikes:
        return {"status": "ok", "alerts_sent": 0, "spikes_detected": 0}

    users = await db["users"].find(SPIKE_RECIPIENT_QUERY).to_list(length=500)
    sent, failed = await _deliver(send_spike_alert, users, spikes[:5])

    await db["pipeline_state"].update_one(
        {"pipeline": "notifications"},
        {
            "$set": {
                "last_spike_check": datetime.now(timezone.utc),
                "last_spikes": spikes[:10],
                "alerts_sent": sent,
                "alerts_failed": failed,
            }
        },
        upsert=True,
    )
    logger.info("Spike alerts: %d spikes, %d sent, %d failed", len(spikes), sent, failed)
    return {
        "status": "ok",
        "spikes_detected": len(spikes),
        "recipients": len(users),
        "alerts_sent": sent,
        "alerts_failed": failed,
    }


async def send_daily_digests(force: bool = False) -> dict:
    """
    Send the top-trends digest to opted-in users.

    The background loop fires once shortly after every startup, so without an
    elapsed-time check a developer restarting the server would mail the same
    digest again each time. `force=True` is for the manual endpoint, where the
    caller has explicitly asked for a send.
    """
    db = await get_database()

    if not force:
        state = await db["pipeline_state"].find_one({"pipeline": "notifications"})
        last_sent = _as_naive_utc((state or {}).get("last_digest_at"))
        if last_sent:
            elapsed_hours = (datetime.utcnow() - last_sent).total_seconds() / 3600
            if elapsed_hours < DIGEST_INTERVAL_HOURS:
                return {
                    "status": "skipped",
                    "reason": "interval_not_elapsed",
                    "hours_since_last": round(elapsed_hours, 2),
                    "interval_hours": DIGEST_INTERVAL_HOURS,
                }

    latest = await db["detected_trends"].find_one(sort=[("calculated_at", -1)])
    if not latest:
        return {"status": "skipped", "reason": "no_trends"}

    batch_time = latest["calculated_at"]
    trends = await db["detected_trends"].find({"calculated_at": batch_time}).sort(
        "trend_score", -1
    ).limit(10).to_list(length=10)

    users = await db["users"].find(DIGEST_RECIPIENT_QUERY).to_list(length=500)
    sent, failed = await _deliver(send_email_digest, users, trends)

    await db["pipeline_state"].update_one(
        {"pipeline": "notifications"},
        {"$set": {
            "last_digest_at": datetime.now(timezone.utc),
            "digests_sent": sent,
            "digests_failed": failed,
        }},
        upsert=True,
    )
    logger.info("Digests: %d recipients, %d sent, %d failed", len(users), sent, failed)
    return {
        "status": "ok",
        "recipients": len(users),
        "digests_sent": sent,
        "digests_failed": failed,
        "topics_included": len(trends),
    }
