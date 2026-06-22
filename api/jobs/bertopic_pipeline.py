"""
Production BERTopic pipeline: raw_tweets -> train -> detected_trends.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from services.notifications import check_and_send_spike_alerts

from db.connection import get_database, deduplicate_existing_trends
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.bertopic_model import BERTopicTrainer, preprocess_bertopic
from services.trend_scoring import clean_keywords, compute_trend_score, dominant_language, generate_topic_label

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "bertopic"
ARTIFACTS_DIR = API_ROOT / "artifacts" / "visualizations"

MIN_CORPUS_SIZE = int(os.getenv("BERTOPIC_MIN_CORPUS_SIZE", "1000"))
CORPUS_LIMIT = int(os.getenv("BERTOPIC_CORPUS_LIMIT", "2000"))


def _adaptive_min_cluster_size(n_docs: int) -> int:
    """Scale HDBSCAN min_cluster_size for small Twitter corpora."""
    return max(3, min(10, n_docs // 5))


def _run_training_sync(df_clean, min_cluster_size: int):
    """Blocking BERTopic train (run in thread pool from async caller)."""
    docs = df_clean["clean_text"].tolist()
    trainer = BERTopicTrainer(min_cluster_size=min_cluster_size)
    topics, _ = trainer.train(docs)
    trainer._training_docs = docs  # noqa: SLF001 — used by hierarchical reduction fix
    return trainer, topics, docs


def _build_trend_documents(df_clean, trainer, topics: list, calculated_at: datetime) -> list:
    """Map BERTopic output to detected_trends MongoDB schema."""
    topic_info = trainer.topic_model.get_topic_info()
    topic_info = topic_info[topic_info["Topic"] != -1]

    max_engagement = 1
    if not df_clean.empty:
        max_engagement = max(1, int((df_clean.get("like_count", 0) + 
        df_clean.get("retweet_count", 0)).max()))

    trend_docs = []
    for _, trow in topic_info.iterrows():
        topic_id = int(trow["Topic"])
        indices = [i for i, t in enumerate(topics) if t == topic_id]
        if not indices:
            continue

        subset = df_clean.iloc[indices]
        volume = len(subset)
        total_likes = int(subset["like_count"].sum())
        total_retweets = int(subset["retweet_count"].sum())
        langs = subset["lang_api"].tolist()

        keywords = trainer.topic_model.get_topic(topic_id)
        representation = clean_keywords([w for w, _ in keywords[:10]] if keywords else [])

        # 1. Waxaan soo akhrineynaa tweets-ka safeysan ee moodelku u calaamadeeyay inay yihiin kuwo tusaale u ah mawduuca (Representative Docs)
        rep_clean_docs = None
        if hasattr(trainer.topic_model, "representative_docs_") and trainer.topic_model.representative_docs_:
            rep_clean_docs = trainer.topic_model.representative_docs_.get(topic_id)
        
        if not rep_clean_docs:
            rep_docs_col = trow.get("Representative_Docs")
            if isinstance(rep_docs_col, (list, np.ndarray)):
                rep_clean_docs = rep_docs_col
            else:
                rep_docs_col = trow.get("Representative_Documents")
                if isinstance(rep_docs_col, (list, np.ndarray)):
                    rep_clean_docs = rep_docs_col

        representative_docs = []
        if rep_clean_docs:
            for clean_doc in rep_clean_docs:
                clean_doc_str = str(clean_doc).strip()
                # 2. Waxaan ku dhex raadineynaa tweets-ka dhabta ah ee database-ka si aan u soo qaadno qoraalkii asalka ahaa
                matching_tweets = subset[subset["clean_text"].str.strip() == clean_doc_str]
                if not matching_tweets.empty:
                    # Waxaan qaadaneynaa qoraalka saxda ah ee asalka ah (text) ee moodelku doortay
                    original_text = matching_tweets.iloc[0]["text"]
                    representative_docs.append(str(original_text))
                else:
                    # Fallback raadin kale ah
                    matching_tweets_orig = subset[subset["text"].str.strip() == clean_doc_str]
                    if not matching_tweets_orig.empty:
                        original_text = matching_tweets_orig.iloc[0]["text"]
                        representative_docs.append(str(original_text))
                    else:
                        # Haddii kale, waxaan dhigeynaa qoraalkii uu moodelku doortay laftiisa
                        representative_docs.append(str(clean_doc))

        # 3. Nadiifin: Waxaan ka saareynaa wixii tweets ah oo soo laalaabtay ama maran (no backend limit)
        seen = set()
        representative_docs = [x for x in representative_docs if x and not (x in seen or seen.add(x))]


        lang_stats = dominant_language(langs)
        en_count = lang_stats["en"]
        so_count = lang_stats["so"]
        others_count = lang_stats["others"]
        total_langs = len(langs)

        en_percentage = round((en_count / total_langs) * 100, 2) if total_langs > 0 else 0.0
        so_percentage = round((so_count / total_langs) * 100, 2) if total_langs > 0 else 0.0
        others_percentage = round((others_count / total_langs) * 100, 2) if total_langs > 0 else 0.0

        trend_docs.append({
            "topic": topic_id,
            "Name": str(trow.get("Name", f"Topic_{topic_id}")),
            "Representation": representation,
            "label": generate_topic_label(representation),
            "representative_docs": representative_docs,
            "volume": volume,
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "trend_score": compute_trend_score(
                volume, total_likes, total_retweets, max_engagement
            ),
            "lang": [l for l in ["en", "so", "others"] if lang_stats[l] > 0],
            "en_count": en_count,
            "so_count": so_count,
            "others_count": others_count,
            "en_percentage": en_percentage,
            "so_percentage": so_percentage,
            "others_percentage": others_percentage,
            "calculated_at": calculated_at,
            "model": "bertopic",
        })

    trend_docs.sort(key=lambda x: x["trend_score"], reverse=True)
    return trend_docs


async def _persist_trends(
    trend_docs: list,
    calculated_at: datetime,
    metrics=None,
    last_trained_tweet_collected_at=None,
) -> int:
    db = await get_database()
    coll = db["detected_trends"]

    # Replace previous BERTopic run entirely so detected_trends always holds
    # exactly one clean set of topics — no accumulation across runs.
    await coll.delete_many({"model": "bertopic"})
    unique_trend_docs = trend_docs

    if unique_trend_docs:
        await coll.insert_many(unique_trend_docs)
        
    state_update = {
        "last_run_at": calculated_at,
        "topics_written": len(unique_trend_docs),
        "status": "success" if unique_trend_docs else "no_topics",
    }
    if metrics:
        state_update["metrics"] = metrics
    if last_trained_tweet_collected_at:
        state_update["last_trained_tweet_collected_at"] = last_trained_tweet_collected_at
        
    await db["pipeline_state"].update_one(
        {"pipeline": "bertopic"},
        {"$set": state_update},
        upsert=True,
    )
    return len(unique_trend_docs)


async def _persist_topic_evolution(trainer, docs: list, df_clean) -> None:
    """Store DTM output when enough temporal spread exists."""
    if len(docs) < MIN_CORPUS_SIZE:
        return
    try:
        timestamps = df_clean["created_at"].tolist()
        topics_over_time = trainer.run_dynamic_topic_modeling(docs, timestamps)
        if topics_over_time is None or topics_over_time.empty:
            return
        db = await get_database()
        records = topics_over_time.to_dict(orient="records")
        for rec in records:
            rec["stored_at"] = datetime.now(timezone.utc)
        await db["topic_evolution"].insert_many(records)
        logger.info("Stored %d topic evolution records.", len(records))
    except Exception as e:
        logger.warning("DTM persistence skipped: %s", e)


async def run_bertopic_pipeline() -> dict:
    """
    End-to-end BERTopic deployment job.
    Returns summary dict for health/logging.
    """
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})
    last_trained_tweet_collected_at = None
    if state:
        last_trained_tweet_collected_at = state.get("last_trained_tweet_collected_at")

    new_tweets_threshold = int(os.getenv("BERTOPIC_NEW_TWEETS_THRESHOLD", "1000"))
    
    if last_trained_tweet_collected_at:
        new_tweets_count = await db["raw_tweets"].count_documents(
            {"collected_at": {"$gt": last_trained_tweet_collected_at}}
        )
        if new_tweets_count < new_tweets_threshold:
            logger.info(
                "Skipping BERTopic: only %d new tweets since last training (minimum %d required)",
                new_tweets_count,
                new_tweets_threshold
            )
            return {
                "status": "skipped",
                "reason": "insufficient_new_tweets",
                "new_tweets_count": new_tweets_count,
                "last_trained_tweet_collected_at": last_trained_tweet_collected_at.isoformat() if hasattr(last_trained_tweet_collected_at, "isoformat") else str(last_trained_tweet_collected_at)
            }
    
    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        logger.info(
            "Skipping BERTopic: corpus size %d < minimum %d",
            count,
            MIN_CORPUS_SIZE,
        )
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
    df_clean = preprocess_bertopic(df, text_col="text")
    if len(df_clean) < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_after_preprocess", "corpus_count": len(df_clean)}

    # Save the prepared clean DataFrame as a CSV for visibility and academic inspection
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        corpus_csv_path = REPORTS_DIR / "latest_clean_corpus.csv"
        df_clean.to_csv(corpus_csv_path, index=False, encoding="utf-8")
        logger.info("Saved latest clean corpus to %s", corpus_csv_path)
    except Exception as e:
        logger.warning("Could not save latest clean corpus CSV: %s", e)

    min_cluster = _adaptive_min_cluster_size(len(df_clean))
    logger.info("Starting BERTopic training on %d documents (min_cluster_size=%d)", len(df_clean), min_cluster)

    trainer, topics, docs = await asyncio.to_thread(
        _run_training_sync, df_clean, min_cluster
    )

    calculated_at = datetime.now(timezone.utc)
    trend_docs = _build_trend_documents(df_clean, trainer, topics, calculated_at)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = str(REPORTS_DIR / "latest_eval_report.txt")
    viz_path = str(ARTIFACTS_DIR / "bertopic_intertopic.html")

    await asyncio.to_thread(
        trainer.generate_evaluation_report, docs, topics, report_path
    )
    try:
        await asyncio.to_thread(trainer.generate_visualization, viz_path)
    except Exception as e:
        logger.warning("Visualization generation failed: %s", e)

    outlier_count = sum(1 for t in topics if t == -1)
    outlier_ratio = outlier_count / len(topics) if topics else 0.0
    cohesion = await asyncio.to_thread(trainer.evaluate_cohesion, docs, topics)
    diversity = await asyncio.to_thread(trainer.calculate_topic_diversity, 10)

    max_collected_at = None
    if not df_clean.empty and "collected_at" in df_clean.columns:
        raw_max = df_clean["collected_at"].max()
        if not pd.isnull(raw_max):
            if hasattr(raw_max, "to_pydatetime"):
                max_collected_at = raw_max.to_pydatetime()
            else:
                max_collected_at = raw_max

    eval_metrics = {
        "semantic_cohesion": round(float(cohesion), 4),
        "topic_diversity": round(float(diversity), 4),
        "outlier_ratio": round(outlier_ratio, 4),
        "num_topics": len(set(topics) - {-1}),
        "corpus_size": len(docs),
    }
    n_written = await _persist_trends(
        trend_docs,
        calculated_at,
        metrics=eval_metrics,
        last_trained_tweet_collected_at=max_collected_at
    )
    await _persist_topic_evolution(trainer, docs, df_clean)

    summary = {
        "status": "success",
        "corpus_count": len(df_clean),
        "topics_written": n_written,
        "outlier_ratio": round(outlier_ratio, 4),
        "calculated_at": calculated_at.isoformat(),
    }
    logger.info("BERTopic pipeline complete: %s", summary)

    if summary.get("status") == "success" and n_written > 0:
        try:
            alert_result = await check_and_send_spike_alerts()
            summary["spike_alerts"] = alert_result
        except Exception as e:
            logger.warning("Spike alert check failed: %s", e)

    return summary
