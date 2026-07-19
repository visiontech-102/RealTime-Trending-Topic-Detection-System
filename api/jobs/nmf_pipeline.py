"""
NMF baseline pipeline: raw_tweets -> preprocess -> train -> evaluate -> reports.
Mirrors lda_pipeline.py and shares the SAME corpus_loader, SAME preprocess_lda
tokenization, and SAME gensim Dictionary construction as LDA, so the two are
directly comparable. Not deployed to production; used for academic comparison.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from db.connection import get_database
from jobs.lda_pipeline import _tokenize_corpus
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.lda_model import prepare_lda_matrices
from services.nmf_model import (
    NMFTrainer,
    calculate_topic_diversity,
    prepare_nmf_matrix,
    run_nmf_grid_search,
)

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "nmf"

# Reuses LDA's env vars deliberately: same corpus thresholds and grid-search
# toggle, so the two baselines cannot drift apart in configuration.
MIN_CORPUS_SIZE = int(os.getenv("LDA_MIN_CORPUS_SIZE", "1000"))
CORPUS_LIMIT = int(os.getenv("LDA_CORPUS_LIMIT", "2000"))
RUN_GRID_SEARCH = os.getenv("LDA_GRID_SEARCH", "true").lower() == "true"
TOPIC_RANGE = list(range(4, 13))  # [4..12] dense range — finds true optimal K, same as LDA
NEW_TWEETS_THRESHOLD = int(os.getenv("LDA_NEW_TWEETS_THRESHOLD", "1000"))  # reuses LDA env var

# _tokenize_corpus is imported from jobs.lda_pipeline (not duplicated) so
# LDA and NMF can never tokenize differently, even after future edits.


def _pick_best_from_grid(results_df) -> dict:
    """Highest C_v coherence; tie-break with smaller K (NMF has no perplexity)."""
    if results_df.empty:
        return {}
    df = results_df.dropna(subset=["coherence"], how="all")
    if df.empty:
        return results_df.iloc[0].to_dict()
    sorted_df = df.sort_values(by=["coherence", "K"], ascending=[False, True])
    return sorted_df.iloc[0].to_dict()


def _run_nmf_sync(tokenized_docs: list, use_grid: bool):
    # Same Dictionary construction (no_below=2, no_above=0.95) as LDA, so both
    # models factorize an identical vocabulary.
    dictionary, _ = prepare_lda_matrices(tokenized_docs, use_tfidf=False)

    if use_grid and len(tokenized_docs) >= 50:
        results_df = run_nmf_grid_search(tokenized_docs, dictionary, topic_range=TOPIC_RANGE)
        best = _pick_best_from_grid(results_df)
        k = int(best.get("K", 8))
        grid_results = results_df.to_dict(orient="records")
    else:
        k = max(3, min(10, len(tokenized_docs) // 15))
        grid_results = []
        best = {"K": k}

    tfidf_matrix, vectorizer = prepare_nmf_matrix(tokenized_docs, dictionary)
    trainer = NMFTrainer(tfidf_matrix, vectorizer)
    trainer.train(num_topics=k)
    coherence, u_mass = trainer.evaluate(tokenized_docs, dictionary)
    topics_vocab = trainer.get_topic_vocabulary_distribution(num_words=8)
    diversity = calculate_topic_diversity(trainer.get_topics(num_words=10))

    return {
        "trainer": trainer,
        "dictionary": dictionary,
        "tokenized_docs": tokenized_docs,
        "num_topics": k,
        "coherence": coherence,
        "u_mass": u_mass,
        "diversity": diversity,
        "grid_results": grid_results,
        "topics_vocab": topics_vocab,
    }


async def _persist_nmf_state(
    result: dict, calculated_at: datetime, last_trained_tweet_collected_at=None
) -> None:
    db = await get_database()
    update_fields = {
        "last_run_at": calculated_at,
        "status": "success",
        "metrics": {
            "coherence_cv": result["coherence"],
            "coherence_umass": result["u_mass"],
            "topic_diversity": result["diversity"],
            "num_topics": result["num_topics"],
            "corpus_size": len(result["tokenized_docs"]),
        },
        "top_topics": result["topics_vocab"],
        "grid_search_ran": bool(result["grid_results"]),
    }
    if last_trained_tweet_collected_at is not None:
        update_fields["last_trained_tweet_collected_at"] = last_trained_tweet_collected_at
    await db["pipeline_state"].update_one(
        {"pipeline": "nmf"},
        {"$set": update_fields},
        upsert=True,
    )


async def run_nmf_pipeline() -> dict:
    """End-to-end NMF baseline job (mirrors run_lda_pipeline)."""
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "nmf"})
    last_trained_tweet_collected_at = state.get("last_trained_tweet_collected_at") if state else None

    if last_trained_tweet_collected_at:
        new_tweets_count = await db["raw_tweets"].count_documents(
            {"collected_at": {"$gt": last_trained_tweet_collected_at}}
        )
        if new_tweets_count < NEW_TWEETS_THRESHOLD:
            logger.info(
                "Skipping NMF: only %d new tweets since last training (minimum %d required)",
                new_tweets_count,
                NEW_TWEETS_THRESHOLD,
            )
            return {
                "status": "skipped",
                "reason": "insufficient_new_tweets",
                "new_tweets_count": new_tweets_count,
            }

    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {
            "status": "skipped",
            "reason": "insufficient_corpus",
            "corpus_count": count,
        }

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
    max_collected_at = None
    if not df.empty and "collected_at" in df.columns:
        raw_max = df["collected_at"].max()
        if not pd.isnull(raw_max):
            max_collected_at = raw_max.to_pydatetime() if hasattr(raw_max, "to_pydatetime") else raw_max

    tokenized_docs = _tokenize_corpus(df)
    if len(tokenized_docs) < MIN_CORPUS_SIZE:
        return {
            "status": "skipped",
            "reason": "insufficient_after_preprocess",
            "corpus_count": len(tokenized_docs),
        }

    logger.info("Starting NMF baseline on %d tokenized documents", len(tokenized_docs))
    result = await asyncio.to_thread(_run_nmf_sync, tokenized_docs, RUN_GRID_SEARCH)

    calculated_at = datetime.now(timezone.utc)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "latest_eval.json"

    report_payload = {
        "generated_at": calculated_at.isoformat(),
        "corpus_size": len(result["tokenized_docs"]),
        "coherence_cv": result["coherence"],
        "coherence_umass": result["u_mass"],
        "topic_diversity": result["diversity"],
        "num_topics": result["num_topics"],
        "top_topics": result["topics_vocab"],
        "grid_results": result["grid_results"][:20],
    }
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    await _persist_nmf_state(result, calculated_at, last_trained_tweet_collected_at=max_collected_at)

    summary = {
        "status": "success",
        "corpus_count": len(result["tokenized_docs"]),
        "num_topics": result["num_topics"],
        "coherence_cv": round(result["coherence"], 4) if result["coherence"] else None,
        "coherence_umass": round(result["u_mass"], 4) if result["u_mass"] else None,
        "topic_diversity": round(result["diversity"], 4) if result["diversity"] else None,
        "calculated_at": calculated_at.isoformat(),
        "report_path": str(report_path),
    }
    logger.info("NMF pipeline complete: %s", summary)
    return summary
