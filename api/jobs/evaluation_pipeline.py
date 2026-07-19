"""
End-to-end three-way model evaluation: trains LDA, NMF, and BERTopic on the
SAME loaded corpus, scores each with C_v coherence (primary), U_Mass
coherence (supporting), and Topic Diversity — split English / Somali —
and writes results to results/metrics/ and results/topics/.

Option 1 K-selection: each model finds its own optimal K independently.
  LDA    : grid search K∈{4..12}, highest C_v, tiebreak K ASC.
  NMF    : grid search K∈{4..12}, highest C_v, tiebreak K ASC.
  BERTopic: HDBSCAN auto-K, unconstrained (its defining characteristic).

Intrinsic metrics only — no labels, no gold-standard.
Perplexity is LDA-only and never used in the three-way comparison.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from db.connection import get_database
from jobs.bertopic_pipeline import _adaptive_min_cluster_size, _run_training_sync
from jobs.lda_pipeline import CORPUS_LIMIT, MIN_CORPUS_SIZE, RUN_GRID_SEARCH, _run_lda_sync, _tokenize_corpus
from jobs.nmf_pipeline import _run_nmf_sync
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.bertopic_model import preprocess_bertopic
from jobs.deployment import persist_deployed_model
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

# Minimum new tweets since last evaluation before re-training all 3 models.
# Prevents unnecessary full re-evaluation when the corpus has not changed.
EVAL_NEW_TWEETS_THRESHOLD = int(os.getenv("EVAL_NEW_TWEETS_THRESHOLD", str(MIN_CORPUS_SIZE)))

logger = logging.getLogger(__name__)

API_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = API_ROOT / "results"
METRICS_DIR = RESULTS_DIR / "metrics"
TOPICS_DIR = RESULTS_DIR / "topics"


async def run_full_evaluation(run_grid_search: bool = None, force: bool = False) -> dict:
    """
    Trains LDA, NMF, and BERTopic on the SAME loaded corpus and scores all
    three with identical intrinsic metrics, split English / Somali (Option B).

    Guard rules (both bypassed by force=True):
      1. Winner already set → always skip. The winner is a one-time academic
         decision; automatic re-selection is disabled by design.
      2. No winner yet but insufficient new data since last attempt → skip.
    """
    use_grid = RUN_GRID_SEARCH if run_grid_search is None else run_grid_search
    db = await get_database()

    if not force:
        # Guard 1: winner already determined — evaluation is a one-time event.
        from jobs.deployment import get_deployed_model
        deployed = await get_deployed_model()
        if deployed is not None:
            logger.info(
                "Evaluation skipped: winner '%s' already set. "
                "Re-evaluation is manual only (POST /jobs/run-evaluation?force=true).",
                deployed,
            )
            return {
                "status": "skipped",
                "reason": "winner_already_set",
                "deployed_model": deployed,
            }

        # Guard 2: not enough new data since last evaluation attempt.
        eval_state = await db["pipeline_state"].find_one({"pipeline": "evaluation"})
        if eval_state:
            last_corpus_max = eval_state.get("last_corpus_max_collected_at")
            if last_corpus_max:
                new_count = await db["raw_tweets"].count_documents(
                    {"collected_at": {"$gt": last_corpus_max}}
                )
                if new_count < EVAL_NEW_TWEETS_THRESHOLD:
                    logger.info(
                        "Evaluation skipped: only %d new tweets since last attempt "
                        "(threshold=%d).",
                        new_count, EVAL_NEW_TWEETS_THRESHOLD,
                    )
                    return {
                        "status": "skipped",
                        "reason": "insufficient_new_tweets_since_last_evaluation",
                        "new_tweets_since_last_eval": new_count,
                        "threshold": EVAL_NEW_TWEETS_THRESHOLD,
                    }

    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)
    if df.empty:
        return {"status": "skipped", "reason": "empty_corpus"}

    # Compute max collected_at from this corpus — saved after evaluation so
    # the guard above knows exactly which tweets were used last time.
    _corpus_max_collected_at = None
    if "collected_at" in df.columns:
        raw_max = df["collected_at"].max()
        if not pd.isnull(raw_max):
            _corpus_max_collected_at = (
                raw_max.to_pydatetime() if hasattr(raw_max, "to_pydatetime") else raw_max
            )

    # Shared evaluation reference corpus/dictionary — SAME for all 3 models.
    reference_corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(reference_corpora)

    # Per-language split — each model trains on its own language corpus independently.
    # This ensures topics are monolingual and C_v is evaluated on matching reference corpora.
    MIN_PER_LANG = 50
    df_en = df[df["lang_api"] == "en"].copy()
    df_so = df[df["lang_api"] == "so"].copy()
    logger.info("Corpus split: EN=%d, SO=%d", len(df_en), len(df_so))

    # --- LDA per-language ---
    lda_tokenized_en = _tokenize_corpus(df_en) if len(df_en) >= MIN_PER_LANG else []
    lda_tokenized_so = _tokenize_corpus(df_so) if len(df_so) >= MIN_PER_LANG else []

    lda_result_en = lda_result_so = None
    if lda_tokenized_en:
        logger.info("Evaluation: training LDA-EN on %d tokenized documents", len(lda_tokenized_en))
        lda_result_en = await asyncio.to_thread(_run_lda_sync, lda_tokenized_en, use_grid)
    if lda_tokenized_so:
        logger.info("Evaluation: training LDA-SO on %d tokenized documents", len(lda_tokenized_so))
        lda_result_so = await asyncio.to_thread(_run_lda_sync, lda_tokenized_so, use_grid)

    lda_topics, K_lda = [], 0
    if lda_result_en:
        lda_topics += get_lda_topics(lda_result_en["trainer"].model)
        K_lda += lda_result_en["num_topics"]
    if lda_result_so:
        lda_topics += get_lda_topics(lda_result_so["trainer"].model)
        K_lda += lda_result_so["num_topics"]
    logger.info("LDA total K=%d (EN=%s, SO=%s)", K_lda,
                lda_result_en["num_topics"] if lda_result_en else 0,
                lda_result_so["num_topics"] if lda_result_so else 0)

    # --- NMF per-language (same tokenized corpus as LDA) ---
    nmf_result_en = nmf_result_so = None
    if lda_tokenized_en:
        logger.info("Evaluation: training NMF-EN on %d tokenized documents", len(lda_tokenized_en))
        nmf_result_en = await asyncio.to_thread(_run_nmf_sync, lda_tokenized_en, use_grid)
    if lda_tokenized_so:
        logger.info("Evaluation: training NMF-SO on %d tokenized documents", len(lda_tokenized_so))
        nmf_result_so = await asyncio.to_thread(_run_nmf_sync, lda_tokenized_so, use_grid)

    nmf_topics, K_nmf = [], 0
    if nmf_result_en:
        nmf_topics += get_nmf_topics(nmf_result_en["trainer"])
        K_nmf += nmf_result_en["num_topics"]
    if nmf_result_so:
        nmf_topics += get_nmf_topics(nmf_result_so["trainer"])
        K_nmf += nmf_result_so["num_topics"]
    logger.info("NMF total K=%d (EN=%s, SO=%s)", K_nmf,
                nmf_result_en["num_topics"] if nmf_result_en else 0,
                nmf_result_so["num_topics"] if nmf_result_so else 0)

    # --- BERTopic per-language (HDBSCAN auto-K per language — its defining characteristic) ---
    df_clean = preprocess_bertopic(df, text_col="text")
    df_clean_en = df_clean[df_clean["lang_api"] == "en"].copy()
    df_clean_so = df_clean[df_clean["lang_api"] == "so"].copy()

    bertopic_topics, K_bertopic = [], 0
    if len(df_clean_en) >= MIN_PER_LANG:
        min_cluster_en = _adaptive_min_cluster_size(len(df_clean_en))
        logger.info("Evaluation: training BERTopic-EN on %d documents (min_cluster=%d)",
                    len(df_clean_en), min_cluster_en)
        trainer_en, _, _ = await asyncio.to_thread(_run_training_sync, df_clean_en, min_cluster_en)
        bt_en = get_bertopic_topics(trainer_en.topic_model)
        bertopic_topics += bt_en
        K_bertopic += len(bt_en)
        logger.info("BERTopic-EN natural K=%d (HDBSCAN, unconstrained)", len(bt_en))

    if len(df_clean_so) >= MIN_PER_LANG:
        min_cluster_so = _adaptive_min_cluster_size(len(df_clean_so))
        logger.info("Evaluation: training BERTopic-SO on %d documents (min_cluster=%d)",
                    len(df_clean_so), min_cluster_so)
        trainer_so, _, _ = await asyncio.to_thread(_run_training_sync, df_clean_so, min_cluster_so)
        bt_so = get_bertopic_topics(trainer_so.topic_model)
        bertopic_topics += bt_so
        K_bertopic += len(bt_so)
        logger.info("BERTopic-SO natural K=%d (HDBSCAN, unconstrained)", len(bt_so))

    logger.info("BERTopic total K=%d", K_bertopic)

    rows = []
    rows += evaluate_model("lda", lda_topics, K_lda, reference_corpora, dictionary)
    rows += evaluate_model("nmf", nmf_topics, K_nmf, reference_corpora, dictionary)
    rows += evaluate_model("bertopic", bertopic_topics, K_bertopic, reference_corpora, dictionary)

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

    eval_at = datetime.now(timezone.utc)

    # Stamp all three pipeline_state entries so run_model_comparison()'s guard passes
    # even on a fresh install where the standalone production pipelines have not yet run.
    # Also write last_trained_tweet_collected_at so each model's deployment guard
    # knows exactly which tweets were used — prevents redundant retraining after restart.
    for _pipeline in ("lda", "nmf", "bertopic"):
        update = {
            "$set": {"last_evaluated_at": eval_at},
            "$setOnInsert": {"last_run_at": eval_at, "status": "evaluated"},
        }
        if _corpus_max_collected_at is not None:
            update["$set"]["last_trained_tweet_collected_at"] = _corpus_max_collected_at
        await db["pipeline_state"].update_one(
            {"pipeline": _pipeline},
            update,
            upsert=True,
        )
    logger.info("Pipeline state markers written for lda, nmf, bertopic.")

    # Option B winner selection: primary = English C_v, tiebreak = Somali C_v.
    # "combined" slice excluded (not an independent measurement).
    winner, _ = _select_winner_from_metrics(rows)
    if winner is None:
        logger.error("Winner selection returned None after a completed evaluation — rows may all be empty.")
        return {"status": "error", "reason": "winner_selection_failed", "rows": rows}
    await persist_deployed_model(winner)
    print(f"Deployed model set to: {winner}")

    # Save evaluation-level state: used by the guard on next startup to avoid
    # retraining on identical data.
    await db["pipeline_state"].update_one(
        {"pipeline": "evaluation"},
        {"$set": {
            "last_evaluated_at":          eval_at,
            "last_corpus_max_collected_at": _corpus_max_collected_at,
            "corpus_size":                len(df),
            "deployed_model":             winner,
        }},
        upsert=True,
    )
    logger.info("Evaluation state saved. corpus_max=%s deployed=%s", _corpus_max_collected_at, winner)

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
        "comparison": comparison_result,
    }
