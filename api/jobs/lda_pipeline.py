"""
LDA baseline pipeline: raw_tweets -> preprocess -> train -> evaluate -> reports.
Not deployed to production; used for academic comparison against BERTopic.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from db.connection import get_database
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.lda_model import (
    LDATrainer,
    get_topic_vocabulary_distribution,
    prepare_lda_matrices,
    preprocess_lda,
    run_lda_grid_search,
)

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = API_ROOT / "reports" / "lda"


MIN_CORPUS_SIZE = int(os.getenv("LDA_MIN_CORPUS_SIZE", "1000"))
CORPUS_LIMIT = int(os.getenv("LDA_CORPUS_LIMIT", "2000"))
RUN_GRID_SEARCH = os.getenv("LDA_GRID_SEARCH", "true").lower() == "true"
NEW_TWEETS_THRESHOLD = int(os.getenv("LDA_NEW_TWEETS_THRESHOLD", "1000"))


def _tokenize_corpus(df) -> list:
    tokenized = []
    for _, row in df.iterrows():
        lang = row.get("lang_api", "en")
        if lang not in ("en", "so"):
            lang = "en"
        tokens = preprocess_lda(str(row.get("text", "")), lang)
        if tokens:
            tokenized.append(tokens)
    return tokenized


def _pick_best_from_grid(results_df) -> dict:
    """Highest C_v coherence; tie-break with smaller K (Occam's razor)."""
    if results_df.empty:
        return {}
    df = results_df.dropna(subset=["coherence"], how="all")
    if df.empty:
        return results_df.iloc[0].to_dict()
    sorted_df = df.sort_values(by=["coherence", "K"], ascending=[False, True])
    return sorted_df.iloc[0].to_dict()


def _run_lda_sync(tokenized_docs: list, use_grid: bool):
    dictionary, corpus = prepare_lda_matrices(tokenized_docs, use_tfidf=False)

    if use_grid and len(tokenized_docs) >= 50:
        topic_range = list(range(4, 13))  # [4,5,6,7,8,9,10,11,12] — dense, finds true optimal K
        results_df = run_lda_grid_search(
            tokenized_docs,
            corpus,
            dictionary,
            topic_range=topic_range,
            alphas=["symmetric"],
            betas=["symmetric"],
        )
        best = _pick_best_from_grid(results_df)
        k = int(best.get("K", 8))
        alpha = best.get("alpha", "symmetric")
        beta = best.get("beta", "symmetric")
        grid_results = results_df.to_dict(orient="records")
    else:
        k = max(3, min(10, len(tokenized_docs) // 15))
        alpha, beta = "symmetric", "symmetric"
        grid_results = []
        best = {"K": k, "alpha": alpha, "beta": beta}

    trainer = LDATrainer(dictionary, corpus)
    trainer.train(num_topics=k, alpha=alpha, eta=beta, passes=10)
    coherence, perplexity = trainer.evaluate(tokenized_docs)
    topics_vocab = get_topic_vocabulary_distribution(trainer.model, num_words=8)

    return {
        "trainer": trainer,
        "dictionary": dictionary,
        "corpus": corpus,
        "tokenized_docs": tokenized_docs,
        "num_topics": k,
        "alpha": alpha,
        "beta": beta,
        "coherence": coherence,
        "perplexity": perplexity,
        "grid_results": grid_results,
        "topics_vocab": topics_vocab,
    }


async def _persist_lda_state(
    result: dict, calculated_at: datetime, last_trained_tweet_collected_at=None
) -> None:
    db = await get_database()
    update_fields = {
        "last_run_at": calculated_at,
        "status": "success",
        "metrics": {
            "coherence_cv": result["coherence"],
            "perplexity": result["perplexity"],
            "num_topics": result["num_topics"],
            "corpus_size": len(result["tokenized_docs"]),
            "alpha": result["alpha"],
            "beta": result["beta"],
        },
        "top_topics": result["topics_vocab"],
        "grid_search_ran": bool(result["grid_results"]),
    }
    if last_trained_tweet_collected_at is not None:
        update_fields["last_trained_tweet_collected_at"] = last_trained_tweet_collected_at
    await db["pipeline_state"].update_one(
        {"pipeline": "lda"},
        {"$set": update_fields},
        upsert=True,
    )


async def run_lda_pipeline() -> dict:
    """End-to-end LDA baseline job."""
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "lda"})
    last_trained_tweet_collected_at = state.get("last_trained_tweet_collected_at") if state else None

    if last_trained_tweet_collected_at:
        new_tweets_count = await db["raw_tweets"].count_documents(
            {"collected_at": {"$gt": last_trained_tweet_collected_at}}
        )
        if new_tweets_count < NEW_TWEETS_THRESHOLD:
            logger.info(
                "Skipping LDA: only %d new tweets since last training (minimum %d required)",
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

    logger.info("Starting LDA baseline on %d tokenized documents", len(tokenized_docs))
    result = await asyncio.to_thread(_run_lda_sync, tokenized_docs, RUN_GRID_SEARCH)

    calculated_at = datetime.now(timezone.utc)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = REPORTS_DIR / "latest_eval.json"

    report_payload = {
        "generated_at": calculated_at.isoformat(),
        "corpus_size": len(tokenized_docs),
        "coherence_cv": result["coherence"],
        "perplexity": result["perplexity"],
        "num_topics": result["num_topics"],
        "hyperparameters": {
            "K": result["num_topics"],
            "alpha": result["alpha"],
            "beta": result["beta"],
        },
        "top_topics": result["topics_vocab"],
        "grid_results": result["grid_results"][:20],
    }
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    await _persist_lda_state(result, calculated_at, last_trained_tweet_collected_at=max_collected_at)

    summary = {
        "status": "success",
        "corpus_count": len(tokenized_docs),
        "num_topics": result["num_topics"],
        "coherence_cv": round(result["coherence"], 4) if result["coherence"] else None,
        "perplexity": round(result["perplexity"], 4) if result["perplexity"] else None,
        "calculated_at": calculated_at.isoformat(),
        "report_path": str(report_path),
    }
    logger.info("LDA pipeline complete: %s", summary)
    return summary
