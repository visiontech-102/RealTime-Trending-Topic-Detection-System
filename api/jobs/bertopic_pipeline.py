"""
Production BERTopic pipeline: raw_tweets -> train -> detected_trends.
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from services.notifications import check_and_send_spike_alerts

from db.connection import get_database, deduplicate_existing_trends
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.bertopic_model import BERTopicTrainer, preprocess_bertopic
from services.evaluation import (
    build_reference_corpora, build_reference_dictionary,
    evaluate_model, get_bertopic_topics,
)
from services.trend_scoring import assign_topic_lang, compute_trend_score, dominant_language, generate_topic_label

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "bertopic"
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
        representation = [w for w, _ in keywords[:10]] if keywords else []

        # For each of the top 3 keywords, find the best original tweet from
        # this topic's document subset that contains that keyword.
        # This guarantees each representative tweet is semantically tied to
        # one specific keyword, and all three are unique.
        _url_re = re.compile(r'https?://\S+')
        seen_norm: set = set()
        representative_docs: list = []

        subset_sorted = subset.copy()
        if "like_count" in subset_sorted.columns and "retweet_count" in subset_sorted.columns:
            subset_sorted = subset_sorted.assign(
                _eng=subset_sorted["like_count"] + subset_sorted["retweet_count"]
            ).sort_values("_eng", ascending=False)

        for keyword in representation[:3]:
            mask = subset_sorted["text"].str.contains(keyword, case=False, na=False)
            candidates = subset_sorted[mask] if mask.any() else subset_sorted
            for _, row in candidates.iterrows():
                tweet = str(row["text"]).strip()
                norm = _url_re.sub('', tweet).strip()
                if norm and norm not in seen_norm:
                    seen_norm.add(norm)
                    representative_docs.append(tweet)
                    break


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
            "lang": assign_topic_lang(langs),
            "en_count": en_count,
            "so_count": so_count,
            "en_percentage": en_percentage,
            "so_percentage": so_percentage,
            "calculated_at": calculated_at,
            "tweet_period_from": subset["collected_at"].min().to_pydatetime() if "collected_at" in subset.columns and not subset["collected_at"].isnull().all() else None,
            "tweet_period_to":   subset["collected_at"].max().to_pydatetime() if "collected_at" in subset.columns and not subset["collected_at"].isnull().all() else None,
            "peak_at": subset["collected_at"].dropna().sort_values().iloc[len(subset["collected_at"].dropna()) // 2].to_pydatetime() if "collected_at" in subset.columns and not subset["collected_at"].isnull().all() else None,
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

    unique_trend_docs = trend_docs
    if unique_trend_docs:
        await coll.insert_many(unique_trend_docs)
        
    current_state = await db["pipeline_state"].find_one({"pipeline": "bertopic"})

    state_update = {
        "last_run_at": calculated_at,
        "topics_written": len(unique_trend_docs),
        "status": "success" if unique_trend_docs else "no_topics",
    }
    if metrics:
        state_update["metrics"] = metrics
        if current_state and current_state.get("metrics"):
            state_update["prev_metrics"] = current_state["metrics"]
    if last_trained_tweet_collected_at:
        state_update["last_trained_tweet_collected_at"] = last_trained_tweet_collected_at

    await db["pipeline_state"].update_one(
        {"pipeline": "bertopic"},
        {"$set": state_update},
        upsert=True,
    )

    if metrics:
        await db["pipeline_history"].insert_one({
            "pipeline":          "bertopic",
            "trained_at":        calculated_at,
            "corpus_size":       metrics.get("corpus_size", 0),
            "num_topics":        metrics.get("num_topics", 0),
            "topics_written":    len(unique_trend_docs),
            "semantic_cohesion": metrics.get("semantic_cohesion"),
            "topic_diversity":   metrics.get("topic_diversity"),
            "outlier_ratio":     metrics.get("outlier_ratio"),
            "c_v_en":            metrics.get("c_v_en"),
            "c_v_so":            metrics.get("c_v_so"),
            "u_mass_en":         metrics.get("u_mass_en"),
            "u_mass_so":         metrics.get("u_mass_so"),
            "diversity_en":      metrics.get("diversity_en"),
            "diversity_so":      metrics.get("diversity_so"),
            "K":                 metrics.get("K"),
        })

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

    new_tweets_threshold = int(os.getenv("BERTOPIC_NEW_TWEETS_THRESHOLD", "500"))

    corpus_after_timestamp = last_trained_tweet_collected_at

    if last_trained_tweet_collected_at:
        new_tweets_count = await db["raw_tweets"].count_documents(
            {"collected_at": {"$gt": last_trained_tweet_collected_at}}
        )
        if new_tweets_count < new_tweets_threshold:
            has_topics = await db["detected_trends"].count_documents({"model": "bertopic"})
            if has_topics > 0:
                logger.info(
                    "Skipping BERTopic: only %d new tweets since last training (minimum %d required)",
                    new_tweets_count,
                    new_tweets_threshold,
                )
                return {
                    "status": "skipped",
                    "reason": "insufficient_new_tweets",
                    "new_tweets_count": new_tweets_count,
                    "last_trained_tweet_collected_at": last_trained_tweet_collected_at.isoformat() if hasattr(last_trained_tweet_collected_at, "isoformat") else str(last_trained_tweet_collected_at),
                }
            # detected_trends empty — first deployment after evaluation.
            # Load all tweets so topics are written immediately.
            logger.info(
                "BERTopic: detected_trends empty after evaluation — loading full corpus (ignoring after_timestamp).",
            )
            corpus_after_timestamp = None

    # New tweets only (incremental) — unless first deployment after evaluation (corpus_after_timestamp=None)
    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT, after_timestamp=corpus_after_timestamp)
    if df.empty:
        return {"status": "skipped", "reason": "no_new_tweets_found"}

    df_clean = preprocess_bertopic(df, text_col="text")
    if df_clean.empty:
        return {"status": "skipped", "reason": "empty_after_preprocess"}

    # Save the prepared clean DataFrame as a CSV for visibility and academic inspection
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        corpus_csv_path = REPORTS_DIR / "latest_clean_corpus.csv"
        df_clean.to_csv(corpus_csv_path, index=False, encoding="utf-8")
        logger.info("Saved latest clean corpus to %s", corpus_csv_path)
    except Exception as e:
        logger.warning("Could not save latest clean corpus CSV: %s", e)

    # ── Per-language split ───────────────────────────────────────────────
    MIN_PER_LANG_CORPUS = 50
    df_en = df_clean[df_clean["lang_api"] == "en"].copy()
    df_so = df_clean[df_clean["lang_api"] == "so"].copy()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    calculated_at = datetime.now(timezone.utc)
    trend_docs_all: list = []

    cohesion_en = 0.0; diversity_en = 0.0; outlier_ratio_en = 0.0; K_en = 0; docs_en: list = []
    cohesion_so = 0.0; diversity_so = 0.0; outlier_ratio_so = 0.0; K_so = 0; docs_so: list = []

    # ── Train EN ─────────────────────────────────────────────────────────
    if len(df_en) >= MIN_PER_LANG_CORPUS:
        min_cluster_en = _adaptive_min_cluster_size(len(df_en))
        logger.info("BERTopic EN: training on %d docs (min_cluster_size=%d)", len(df_en), min_cluster_en)
        trainer_en, topics_en, docs_en = await asyncio.to_thread(_run_training_sync, df_en, min_cluster_en)

        td_en = _build_trend_documents(df_en, trainer_en, topics_en, calculated_at)
        for doc in td_en:
            doc["lang"] = "en"
        trend_docs_all.extend(td_en)

        K_en = len(set(topics_en) - {-1})
        outlier_ratio_en = sum(1 for t in topics_en if t == -1) / len(topics_en) if topics_en else 0.0
        cohesion_en = await asyncio.to_thread(trainer_en.evaluate_cohesion, docs_en, topics_en)
        diversity_en = await asyncio.to_thread(trainer_en.calculate_topic_diversity, 10)

        report_path = str(REPORTS_DIR / "latest_eval_report.txt")
        await asyncio.to_thread(trainer_en.generate_evaluation_report, docs_en, topics_en, report_path)
        await _persist_topic_evolution(trainer_en, docs_en, df_en)
    else:
        logger.warning("BERTopic EN: skipped — only %d docs (minimum %d)", len(df_en), MIN_PER_LANG_CORPUS)

    # ── Train SO ─────────────────────────────────────────────────────────
    if len(df_so) >= MIN_PER_LANG_CORPUS:
        min_cluster_so = _adaptive_min_cluster_size(len(df_so))
        logger.info("BERTopic SO: training on %d docs (min_cluster_size=%d)", len(df_so), min_cluster_so)
        trainer_so, topics_so, docs_so = await asyncio.to_thread(_run_training_sync, df_so, min_cluster_so)

        td_so = _build_trend_documents(df_so, trainer_so, topics_so, calculated_at)
        for doc in td_so:
            doc["lang"] = "so"
        trend_docs_all.extend(td_so)

        K_so = len(set(topics_so) - {-1})
        outlier_ratio_so = sum(1 for t in topics_so if t == -1) / len(topics_so) if topics_so else 0.0
        cohesion_so = await asyncio.to_thread(trainer_so.evaluate_cohesion, docs_so, topics_so)
        diversity_so = await asyncio.to_thread(trainer_so.calculate_topic_diversity, 10)
    else:
        logger.warning("BERTopic SO: skipped — only %d docs (minimum %d)", len(df_so), MIN_PER_LANG_CORPUS)

    if not trend_docs_all:
        return {"status": "skipped", "reason": "insufficient_per_language_corpus",
                "en_docs": len(df_en), "so_docs": len(df_so)}

    # ── Combined metrics (outlier_ratio — BERTopic specific) ─────────────
    n_en, n_so = len(docs_en), len(docs_so)
    n_total = n_en + n_so or 1

    if n_en > 0 and n_so > 0:
        outlier_ratio = (outlier_ratio_en * n_en + outlier_ratio_so * n_so) / n_total
    elif n_en > 0:
        outlier_ratio = outlier_ratio_en
    else:
        outlier_ratio = outlier_ratio_so

    # ── Standardized metrics — gensim C_v (same method as evaluation_pipeline) ──
    all_bertopic_topics = []
    if n_en > 0:
        all_bertopic_topics += get_bertopic_topics(trainer_en.topic_model)
    if n_so > 0:
        all_bertopic_topics += get_bertopic_topics(trainer_so.topic_model)

    def _eval_sync():
        ref = build_reference_corpora(df_clean)
        dic = build_reference_dictionary(ref)
        return evaluate_model("bertopic", all_bertopic_topics, K_en + K_so, ref, dic)

    std_rows = await asyncio.to_thread(_eval_sync)
    std_en = next((r for r in std_rows if r["language"] == "en"), {})
    std_so = next((r for r in std_rows if r["language"] == "so"), {})

    c_v_en = std_en.get("c_v")
    c_v_so = std_so.get("c_v")
    if c_v_en is not None and c_v_so is not None:
        semantic_cohesion = round((c_v_en + c_v_so) / 2, 4)
    else:
        semantic_cohesion = c_v_en or c_v_so or 0.0

    max_collected_at = None
    if not df_clean.empty and "collected_at" in df_clean.columns:
        raw_max = df_clean["collected_at"].max()
        if not pd.isnull(raw_max):
            max_collected_at = raw_max.to_pydatetime() if hasattr(raw_max, "to_pydatetime") else raw_max

    eval_metrics = {
        "semantic_cohesion": round(float(semantic_cohesion), 4),
        "topic_diversity":   std_en.get("diversity") or std_so.get("diversity"),
        "outlier_ratio":     round(outlier_ratio, 4),
        "num_topics":        K_en + K_so,
        "corpus_size":       n_total,
        "c_v_en":            c_v_en,
        "c_v_so":            c_v_so,
        "u_mass_en":         std_en.get("u_mass"),
        "u_mass_so":         std_so.get("u_mass"),
        "diversity_en":      std_en.get("diversity"),
        "diversity_so":      std_so.get("diversity"),
        "K":                 K_en + K_so,
    }

    trend_docs_all.sort(key=lambda x: x["trend_score"], reverse=True)
    n_written = await _persist_trends(
        trend_docs_all, calculated_at,
        metrics=eval_metrics,
        last_trained_tweet_collected_at=max_collected_at,
    )

    summary = {
        "status": "success",
        "corpus_count": n_total,
        "topics_written": n_written,
        "en_topics": K_en,
        "so_topics": K_so,
        "outlier_ratio": round(outlier_ratio, 4),
        "calculated_at": calculated_at.isoformat(),
    }
    logger.info("BERTopic pipeline complete: %s", summary)

    if n_written > 0:
        try:
            alert_result = await check_and_send_spike_alerts()
            summary["spike_alerts"] = alert_result
        except Exception as e:
            logger.warning("Spike alert check failed: %s", e)

    return summary
