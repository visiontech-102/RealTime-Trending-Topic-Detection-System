"""MongoDB integration tests (skipped if MongoDB is not running)."""
from datetime import datetime, timezone

import os
import pytest

try:
    from pymongo import MongoClient
    _client = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=2000)
    _client.admin.command("ping")
    _client.close()
    _MONGO_OK = True
except Exception:
    _MONGO_OK = False

pytestmark = pytest.mark.skipif(not _MONGO_OK, reason="MongoDB not available at MONGODB_URL")


@pytest.mark.asyncio
async def test_corpus_loader_reads_inserted_tweets(test_db):
    from pipelines.corpus_loader import load_tweet_corpus, get_corpus_count

    await test_db["raw_tweets"].insert_many([
        {
            "id": "t1",
            "text": "Government announces new economic policy today",
            "lang_api": "en",
            "created_at": datetime.now(timezone.utc),
            "collected_at": datetime.now(timezone.utc),
            "like_count": 10,
            "retweet_count": 2,
        },
        {
            "id": "t2",
            "text": "Dowladda waxay soo saartay qorshe cusub",
            "lang_api": "so",
            "created_at": datetime.now(timezone.utc),
            "collected_at": datetime.now(timezone.utc),
            "like_count": 5,
            "retweet_count": 1,
        },
    ])

    count = await get_corpus_count()
    assert count == 2

    df = await load_tweet_corpus(limit=10)
    assert len(df) == 2
    assert "text" in df.columns


@pytest.mark.asyncio
async def test_detected_trends_latest_batch_query(test_db):
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=2)

    await test_db["detected_trends"].insert_many([
        {
            "Name": "Old Topic",
            "Representation": ["old"],
            "trend_score": 30.0,
            "lang": "en",
            "calculated_at": earlier,
            "model": "bertopic",
        },
        {
            "Name": "New Topic EN",
            "Representation": ["politics", "vote"],
            "trend_score": 75.0,
            "lang": "en",
            "calculated_at": now,
            "model": "bertopic",
        },
        {
            "Name": "New Topic SO",
            "Representation": ["dowladda"],
            "trend_score": 60.0,
            "lang": "so",
            "calculated_at": now,
            "model": "bertopic",
        },
    ])

    latest = await test_db["detected_trends"].find_one(sort=[("calculated_at", -1)])
    batch_time = latest["calculated_at"]
    en_trends = await test_db["detected_trends"].find(
        {"calculated_at": batch_time, "lang": {"$in": ["en", "mixed"]}}
    ).to_list(length=10)

    assert len(en_trends) == 1
    assert en_trends[0]["Name"] == "New Topic EN"


@pytest.mark.asyncio
async def test_pipeline_state_upsert(test_db):
    now = datetime.now(timezone.utc)
    await test_db["pipeline_state"].update_one(
        {"pipeline": "bertopic"},
        {"$set": {"last_run_at": now, "metrics": {"semantic_cohesion": 0.45}}},
        upsert=True,
    )
    state = await test_db["pipeline_state"].find_one({"pipeline": "bertopic"})
    assert state["metrics"]["semantic_cohesion"] == 0.45


@pytest.mark.asyncio
async def test_model_comparison_with_pipeline_states(test_db):
    from jobs.model_comparison import run_model_comparison

    now = datetime.now(timezone.utc)
    await test_db["pipeline_state"].insert_many([
        {
            "pipeline": "lda",
            "metrics": {"coherence_cv": 0.42, "perplexity": -8.5, "num_topics": 8},
            "last_run_at": now,
        },
        {
            "pipeline": "bertopic",
            "metrics": {"semantic_cohesion": 0.48, "topic_diversity": 0.9, "outlier_ratio": 0.1},
            "last_run_at": now,
        },
    ])

    result = await run_model_comparison()
    assert result["status"] == "success"
    assert result["selected_deployment_model"] == "bertopic"
    assert len(result["criteria_comparison"]) == 8

    stored = await test_db["pipeline_state"].find_one({"pipeline": "model_comparison"})
    assert stored is not None
