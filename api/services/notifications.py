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

    users = await db["users"].find({"spike_alerts": True}).to_list(length=500)
    sent = 0
    for user in users:
        email = user.get("email")
        if email:
            await send_spike_alert(email, spikes[:5])
            sent += 1

    await db["pipeline_state"].update_one(
        {"pipeline": "notifications"},
        {
            "$set": {
                "last_spike_check": datetime.now(timezone.utc),
                "last_spikes": spikes[:10],
                "alerts_sent": sent,
            }
        },
        upsert=True,
    )
    logger.info("Spike alerts: %d spikes, %d emails sent", len(spikes), sent)
    return {"status": "ok", "spikes_detected": len(spikes), "alerts_sent": sent}


async def send_daily_digests() -> dict:
    """Send top trends digest to users with email_digests enabled."""
    db = await get_database()
    latest = await db["detected_trends"].find_one(sort=[("calculated_at", -1)])
    if not latest:
        return {"status": "skipped", "reason": "no_trends"}

    batch_time = latest["calculated_at"]
    trends = await db["detected_trends"].find({"calculated_at": batch_time}).sort(
        "trend_score", -1
    ).limit(10).to_list(length=10)

    users = await db["users"].find({"email_digests": True}).to_list(length=500)
    sent = 0
    for user in users:
        email = user.get("email")
        if email:
            await send_email_digest(email, trends)
            sent += 1

    await db["pipeline_state"].update_one(
        {"pipeline": "notifications"},
        {"$set": {"last_digest_at": datetime.now(timezone.utc), "digests_sent": sent}},
        upsert=True,
    )
    return {"status": "ok", "digests_sent": sent, "topics_included": len(trends)}
