"""
Operational checks for ingestion and training pipelines.
"""
import os
from datetime import datetime, timezone

from db.connection import get_database

BERTOPIC_MIN = int(os.getenv("BERTOPIC_MIN_CORPUS_SIZE", "1000"))
LDA_MIN = int(os.getenv("LDA_MIN_CORPUS_SIZE", "1000"))
OUTLIER_WARN_THRESHOLD = float(os.getenv("BERTOPIC_OUTLIER_WARN_RATIO", "0.35"))


async def collect_system_status() -> dict:
    """Gather monitoring snapshot for /health and alerts."""
    db = await get_database()
    alerts = []

    raw_count = await db["raw_tweets"].count_documents({})
    last_tweet = await db["raw_tweets"].find_one(sort=[("collected_at", -1)])
    lda_state = await db["pipeline_state"].find_one({"pipeline": "lda"})
    bertopic_state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})
    comparison_state = await db["pipeline_state"].find_one({"pipeline": "model_comparison"})
    notifications_state = await db["pipeline_state"].find_one({"pipeline": "notifications"})

    if raw_count < BERTOPIC_MIN:
        alerts.append({
            "level": "info",
            "code": "low_corpus",
            "message": f"Corpus {raw_count} tweets below BERTopic minimum {BERTOPIC_MIN}",
        })

    bt_metrics = (bertopic_state or {}).get("metrics") or {}
    outlier_ratio = bt_metrics.get("outlier_ratio")
    if outlier_ratio is not None and outlier_ratio > OUTLIER_WARN_THRESHOLD:
        alerts.append({
            "level": "warning",
            "code": "high_outlier_ratio",
            "message": f"BERTopic Topic -1 ratio {outlier_ratio:.1%} exceeds {OUTLIER_WARN_THRESHOLD:.0%}",
        })

    if bertopic_state and bertopic_state.get("status") == "no_topics":
        alerts.append({
            "level": "warning",
            "code": "no_topics_detected",
            "message": "Last BERTopic run produced no deployable topics",
        })

    if raw_count >= LDA_MIN and not lda_state:
        alerts.append({
            "level": "info",
            "code": "lda_not_run",
            "message": "LDA baseline has not been executed yet",
        })

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "raw_tweet_count": raw_count,
        "last_ingestion_at": last_tweet.get("collected_at") if last_tweet else None,
        "lda_pipeline": lda_state or {},
        "bertopic_pipeline": bertopic_state or {},
        "model_comparison": comparison_state or {},
        "notifications": notifications_state or {},
        "thresholds": {
            "bertopic_min_corpus": BERTOPIC_MIN,
            "lda_min_corpus": LDA_MIN,
            "outlier_warn_ratio": OUTLIER_WARN_THRESHOLD,
        },
        "alerts": alerts,
    }
