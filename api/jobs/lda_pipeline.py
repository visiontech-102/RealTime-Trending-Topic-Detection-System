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
ARTIFACTS_DIR = API_ROOT / "artifacts" / "visualizations"

MIN_CORPUS_SIZE = int(os.getenv("LDA_MIN_CORPUS_SIZE", "1000"))
CORPUS_LIMIT = int(os.getenv("LDA_CORPUS_LIMIT", "2000"))
RUN_GRID_SEARCH = os.getenv("LDA_GRID_SEARCH", "true").lower() == "true"


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
    """Highest coherence; tie-break with lower perplexity."""
    if results_df.empty:
        return {}
    df = results_df.dropna(subset=["coherence"], how="all")
    if df.empty:
        return results_df.iloc[0].to_dict()
    sorted_df = df.sort_values(by=["coherence", "perplexity"], ascending=[False, True])
    return sorted_df.iloc[0].to_dict()


def _run_lda_sync(tokenized_docs: list, use_grid: bool):
    dictionary, corpus = prepare_lda_matrices(tokenized_docs, use_tfidf=False)

    if use_grid and len(tokenized_docs) >= 50:
        topic_range = [5, 8, 10, 12]
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


async def _persist_lda_state(result: dict, calculated_at: datetime) -> None:
    db = await get_database()
    await db["pipeline_state"].update_one(
        {"pipeline": "lda"},
        {
            "$set": {
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
        },
        upsert=True,
    )


async def run_lda_pipeline() -> dict:
    """End-to-end LDA baseline job."""
    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {
            "status": "skipped",
            "reason": "insufficient_corpus",
            "corpus_count": count,
        }

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
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
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = REPORTS_DIR / "latest_eval.json"
    viz_path = ARTIFACTS_DIR / "lda_intertopic.html"

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

    try:
        await asyncio.to_thread(
            result["trainer"].generate_visualization, str(viz_path)
        )
    except Exception as e:
        logger.warning("pyLDAvis generation failed: %s", e)

    await _persist_lda_state(result, calculated_at)

    summary = {
        "status": "success",
        "corpus_count": len(tokenized_docs),
        "num_topics": result["num_topics"],
        "coherence_cv": round(result["coherence"], 4) if result["coherence"] else None,
        "perplexity": round(result["perplexity"], 4) if result["perplexity"] else None,
        "calculated_at": calculated_at.isoformat(),
        "report_path": str(report_path),
        "visualization_path": str(viz_path),
    }
    logger.info("LDA pipeline complete: %s", summary)
    return summary
