"""
End-to-end three-way model evaluation: trains LDA, NMF, and BERTopic on the
SAME loaded corpus, scores each with C_v coherence (primary), U_Mass
coherence (supporting), and Topic Diversity — split English / Somali /
combined — and writes results to results/metrics/ and results/topics/.

Intrinsic metrics only: there are no labels for this task, so no
accuracy/precision/recall/F1 and no gold-standard. Perplexity is LDA-only
and is never used in the three-way comparison (NMF is non-probabilistic).
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from db.connection import get_database
from jobs.bertopic_pipeline import _adaptive_min_cluster_size, _run_training_sync
from jobs.lda_pipeline import CORPUS_LIMIT, MIN_CORPUS_SIZE, RUN_GRID_SEARCH, _run_lda_sync, _tokenize_corpus
from jobs.nmf_pipeline import _run_nmf_sync
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.bertopic_model import preprocess_bertopic
from jobs.deployment import persist_deployed_model
from jobs.enhancement import run_enhancement
from jobs.model_comparison import _select_winner_from_metrics, run_model_comparison
from services.evaluation import (
    build_reference_corpora,
    build_reference_dictionary,
    evaluate_model,
    get_bertopic_topics,
    get_lda_topics,
    get_nmf_topics,
    save_metrics_table,
    save_topic_words,
)

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = API_ROOT / "results"
METRICS_DIR = RESULTS_DIR / "metrics"
TOPICS_DIR = RESULTS_DIR / "topics"


async def run_full_evaluation(run_grid_search: bool = None) -> dict:
    """
    Trains LDA, NMF, and BERTopic on the SAME loaded corpus (CORPUS_LIMIT is
    LDA's own env-driven constant, reused here so all three never drift
    apart on corpus size) and scores all three with identical intrinsic
    metrics, split en / so / combined.
    """
    use_grid = RUN_GRID_SEARCH if run_grid_search is None else run_grid_search

    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
    if df.empty:
        return {"status": "skipped", "reason": "empty_corpus"}

    # Shared evaluation reference corpus/dictionary — SAME for all 3 models.
    reference_corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(reference_corpora)

    # --- LDA ---
    lda_tokenized = _tokenize_corpus(df)
    logger.info("Evaluation: training LDA on %d tokenized documents", len(lda_tokenized))
    lda_result = await asyncio.to_thread(_run_lda_sync, lda_tokenized, use_grid)
    lda_topics = get_lda_topics(lda_result["trainer"].model)

    # --- NMF (SAME tokenized corpus as LDA) ---
    logger.info("Evaluation: training NMF on %d tokenized documents", len(lda_tokenized))
    nmf_result = await asyncio.to_thread(_run_nmf_sync, lda_tokenized, use_grid)
    nmf_topics = get_nmf_topics(nmf_result["trainer"])

    # --- BERTopic (SAME source df, its own minimal preprocessing) ---
    df_clean = preprocess_bertopic(df, text_col="text")
    min_cluster = _adaptive_min_cluster_size(len(df_clean))
    logger.info("Evaluation: training BERTopic on %d documents", len(df_clean))
    bertopic_trainer, _, _ = await asyncio.to_thread(_run_training_sync, df_clean, min_cluster)
    bertopic_topics = get_bertopic_topics(bertopic_trainer.topic_model)

    rows = []
    rows += evaluate_model("lda", lda_topics, lda_result["num_topics"], reference_corpora, dictionary)
    rows += evaluate_model("nmf", nmf_topics, nmf_result["num_topics"], reference_corpora, dictionary)
    rows += evaluate_model("bertopic", bertopic_topics, len(bertopic_topics), reference_corpora, dictionary)

    saved_metrics = save_metrics_table(rows, METRICS_DIR)
    saved_topics = {
        "lda": save_topic_words("lda", lda_topics, reference_corpora, TOPICS_DIR),
        "nmf": save_topic_words("nmf", nmf_topics, reference_corpora, TOPICS_DIR),
        "bertopic": save_topic_words("bertopic", bertopic_topics, reference_corpora, TOPICS_DIR),
    }

    print(f"Saved metrics CSV:  {saved_metrics['csv']}")
    print(f"Saved metrics JSON: {saved_metrics['json']}")
    for model_name, paths in saved_topics.items():
        for language, path in paths.items():
            print(f"Saved topics CSV ({model_name}, {language}): {path}")

    # Stamp all three pipeline_state entries so run_model_comparison()'s guard passes
    # even on a fresh install where the standalone production pipelines have not yet run.
    # $setOnInsert: only written when the document is newly created (upsert inserts) —
    # existing entries from production pipeline runs keep their full metrics intact.
    eval_at = datetime.now(timezone.utc)
    _db = await get_database()
    for _pipeline in ("lda", "nmf", "bertopic"):
        await _db["pipeline_state"].update_one(
            {"pipeline": _pipeline},
            {
                "$set":         {"last_evaluated_at": eval_at},
                "$setOnInsert": {"last_run_at": eval_at, "status": "evaluated"},
            },
            upsert=True,
        )
    logger.info("Pipeline state markers written for lda, nmf, bertopic.")

    # Select winner and persist so the deployment loop knows which model to retrain.
    winner, _ = _select_winner_from_metrics(rows)
    if winner is None:
        logger.error("Winner selection returned None after a completed evaluation — rows may all be empty.")
        return {"status": "error", "reason": "winner_selection_failed", "rows": rows}
    await persist_deployed_model(winner)
    print(f"Deployed model set to: {winner}")

    try:
        enhancement_result = await run_enhancement(winner)
        logger.info(
            "Enhancement complete for winner '%s': status=%s",
            winner, enhancement_result.get("status"),
        )
    except Exception:
        logger.warning(
            "Enhancement failed for winner '%s' — continuing to comparison.",
            winner, exc_info=True,
        )
        enhancement_result = {"status": "error", "reason": "enhancement_exception"}

    # Sync the comparison report to the evaluation that just ran.
    # run_model_comparison() calls persist_deployed_model(winner) internally;
    # that is an idempotent upsert and will agree with the call above because
    # both read from the same coherence_diversity.json we just wrote.
    try:
        comparison_result = await run_model_comparison()
        logger.info("Comparison report synced after evaluation: status=%s", comparison_result.get("status"))
    except Exception:
        logger.warning(
            "Model comparison failed after evaluation — core results are still saved.",
            exc_info=True,
        )
        comparison_result = {"status": "error", "reason": "comparison_exception"}

    return {
        "status": "success",
        "deployed_model": winner,
        "rows": rows,
        "metrics_paths": {k: str(v) for k, v in saved_metrics.items()},
        "topics_paths": {m: {l: str(p) for l, p in paths.items()} for m, paths in saved_topics.items()},
        "enhancement": enhancement_result,
        "comparison": comparison_result,
    }
