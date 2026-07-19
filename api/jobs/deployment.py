"""
Deployment-model registry and winner-only retraining dispatcher.

After run_full_evaluation() saves results/metrics/coherence_diversity.json and
selects a winner, persist_deployed_model() records that name in pipeline_state.
main.py's periodic_winner_training_loop calls run_deployed_pipeline() on every
tick — only the winning model retrains; the two losing models stay frozen with
their last artifacts intact.

LDA and NMF each have a full deployment path (_run_lda_deployment /
_run_nmf_deployment) that writes to detected_trends using the same schema
BERTopic writes, so the dashboard and API routes need no changes regardless of
which model wins.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from db.connection import deduplicate_existing_trends, get_database
from jobs.lda_pipeline import CORPUS_LIMIT, MIN_CORPUS_SIZE, RUN_GRID_SEARCH, _run_lda_sync
from jobs.nmf_pipeline import _run_nmf_sync
from pipelines.corpus_loader import get_corpus_count, load_tweet_corpus
from services.evaluation import (
    build_reference_corpora, build_reference_dictionary,
    evaluate_model, get_lda_topics, get_nmf_topics,
)
from services.lda_model import preprocess_lda
from services.nmf_model import prepare_nmf_matrix
from services.trend_scoring import assign_topic_lang, clean_keywords, compute_trend_score, dominant_language, generate_topic_label

logger = logging.getLogger(__name__)

# How many genuinely new tweets must have arrived before the deployed model
# retrains. Overridable via env var so the user can tune without code changes.
DEPLOYED_RETRAIN_THRESHOLD = int(os.getenv("DEPLOYED_MODEL_RETRAIN_THRESHOLD", "500"))


# ---------------------------------------------------------------------------
# Registry — persist and read the winning model name
# ---------------------------------------------------------------------------

async def persist_deployed_model(model_name: str) -> None:
    """Write the winning model name to pipeline_state so main.py reads it."""
    db = await get_database()
    await db["pipeline_state"].update_one(
        {"pipeline": "deployed_model"},
        {"$set": {"model": model_name, "set_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    logger.info("Deployed model persisted: %s", model_name)


async def get_deployed_model() -> Optional[str]:
    """Return the deployed model name, or None if no evaluation has run yet."""
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "deployed_model"})
    if not state:
        return None
    return state.get("model") or None


# ---------------------------------------------------------------------------
# Dispatcher — only the winner runs
# ---------------------------------------------------------------------------

async def run_deployed_pipeline() -> dict:
    """Retrain only the deployed model. Losing models are never called here."""
    deployed = await get_deployed_model()
    if deployed is None:
        logger.info("Deployment loop: no winner selected — run python run_evaluation.py first.")
        return {"status": "skipped", "reason": "no_winner_selected"}
    logger.info("Deployment loop: retraining deployed model '%s'", deployed)
    if deployed == "lda":
        return await _run_lda_deployment()
    if deployed == "nmf":
        return await _run_nmf_deployment()
    if deployed == "bertopic":
        from jobs.bertopic_pipeline import run_bertopic_pipeline
        return await run_bertopic_pipeline()
    logger.error("Deployment loop: unknown model '%s'", deployed)
    return {"status": "error", "reason": "unknown_model", "model": deployed}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _tokenize_with_indices(df: pd.DataFrame) -> tuple:
    """
    Identical tokenisation to _tokenize_corpus in lda_pipeline.py, but also
    returns the df row indices that survived so we can re-align tokenized
    documents with the original df rows for topic-to-document mapping.
    """
    valid_idx: list = []
    valid_tokens: list = []
    for idx, row in df.iterrows():
        lang = row.get("lang_api", "en")
        if lang not in ("en", "so"):
            lang = "en"
        tokens = preprocess_lda(str(row.get("text", "")), lang)
        if tokens:
            valid_idx.append(idx)
            valid_tokens.append(tokens)
    return valid_tokens, valid_idx


async def _persist_trend_docs(
    trend_docs: list, calculated_at: datetime, model_name: str
) -> int:
    """
    Write trend_docs to detected_trends using the same dedup logic as
    BERTopic's _persist_trends, then update pipeline_state for model_name.
    """
    db = await get_database()
    coll = db["detected_trends"]

    # Replace previous run for this model entirely — one clean set, no accumulation.
    await coll.delete_many({"model": model_name})
    unique = trend_docs

    if unique:
        await coll.insert_many(unique)

    await db["pipeline_state"].update_one(
        {"pipeline": model_name},
        {"$set": {
            "last_run_at": calculated_at,
            "status": "success",
            "topics_written": len(unique),
        }},
        upsert=True,
    )
    return len(unique)


async def _update_last_trained_timestamp(model_name: str, df: pd.DataFrame) -> None:
    """
    Store max(collected_at) of the training corpus so the Step-4 gate can
    count genuinely new tweets on the next tick.
    """
    if df.empty or "collected_at" not in df.columns:
        return
    raw_max = df["collected_at"].max()
    if pd.isnull(raw_max):
        return
    max_ts = raw_max.to_pydatetime() if hasattr(raw_max, "to_pydatetime") else raw_max
    db = await get_database()
    await db["pipeline_state"].update_one(
        {"pipeline": model_name},
        {"$set": {"last_trained_tweet_collected_at": max_ts}},
        upsert=True,
    )


async def _write_pipeline_history(
    db,
    model_name: str,
    calculated_at: datetime,
    corpus_size: int,
    num_topics: int,
    topics_written: int,
    semantic_cohesion=None,
    topic_diversity=None,
    outlier_ratio=None,
    c_v_en=None,
    c_v_so=None,
    u_mass_en=None,
    u_mass_so=None,
    diversity_en=None,
    diversity_so=None,
) -> None:
    await db["pipeline_history"].insert_one({
        "pipeline":          model_name,
        "trained_at":        calculated_at,
        "corpus_size":       corpus_size,
        "num_topics":        num_topics,
        "topics_written":    topics_written,
        "K":                 num_topics,
        "semantic_cohesion": semantic_cohesion,
        "topic_diversity":   topic_diversity,
        "outlier_ratio":     outlier_ratio,
        "c_v_en":            c_v_en,
        "c_v_so":            c_v_so,
        "u_mass_en":         u_mass_en,
        "u_mass_so":         u_mass_so,
        "diversity_en":      diversity_en,
        "diversity_so":      diversity_so,
    })


def _compute_eval_rows_sync(df: pd.DataFrame, model_name: str, topics: list, K: int) -> list:
    """Compute standardized gensim C_v metrics — identical method to evaluation_pipeline.py."""
    reference_corpora = build_reference_corpora(df)
    dictionary = build_reference_dictionary(reference_corpora)
    return evaluate_model(model_name, topics, K, reference_corpora, dictionary)


def _extract_metrics_from_rows(rows: list) -> dict:
    """Extract per-language metrics from evaluate_model() rows into pipeline_history fields."""
    en = next((r for r in rows if r["language"] == "en"), {})
    so = next((r for r in rows if r["language"] == "so"), {})
    c_v_en = en.get("c_v")
    c_v_so = so.get("c_v")
    if c_v_en is not None and c_v_so is not None:
        semantic_cohesion = round((c_v_en + c_v_so) / 2, 4)
    else:
        semantic_cohesion = c_v_en or c_v_so
    return {
        "semantic_cohesion": semantic_cohesion,
        "c_v_en":            c_v_en,
        "c_v_so":            c_v_so,
        "u_mass_en":         en.get("u_mass"),
        "u_mass_so":         so.get("u_mass"),
        "topic_diversity":   en.get("diversity") or so.get("diversity"),
        "diversity_en":      en.get("diversity"),
        "diversity_so":      so.get("diversity"),
    }


def _tweet_period(subset: pd.DataFrame) -> dict:
    """Return tweet_period_from / tweet_period_to / peak_at from subset's collected_at column."""
    if "collected_at" not in subset.columns or subset["collected_at"].isnull().all():
        return {"tweet_period_from": None, "tweet_period_to": None, "peak_at": None}
    col = subset["collected_at"].dropna().sort_values()
    def _to_dt(v):
        return v.to_pydatetime() if hasattr(v, "to_pydatetime") else v
    median_val = col.iloc[len(col) // 2]
    return {
        "tweet_period_from": _to_dt(col.min()),
        "tweet_period_to":   _to_dt(col.max()),
        "peak_at":           _to_dt(median_val),
    }


def _max_engagement(df_subset: pd.DataFrame, df_full: pd.DataFrame) -> int:
    """Max total engagement across the full loaded corpus (same as BERTopic uses)."""
    likes = df_full["like_count"] if "like_count" in df_full.columns else pd.Series([0])
    rts = df_full["retweet_count"] if "retweet_count" in df_full.columns else pd.Series([0])
    return max(1, int((likes + rts).max()))


def _lang_fields(subset: pd.DataFrame) -> dict:
    """Compute language breakdown fields from a topic's document subset."""
    langs = subset["lang_api"].tolist() if "lang_api" in subset.columns else []
    stats = dominant_language(langs)
    n = len(langs) or 1
    return {
        "lang": assign_topic_lang(langs),
        "en_count": stats["en"],
        "so_count": stats["so"],
        "others_count": stats["others"],
        "en_percentage": round(stats["en"] / n * 100, 2),
        "so_percentage": round(stats["so"] / n * 100, 2),
        "others_percentage": round(stats["others"] / n * 100, 2),
    }


# ---------------------------------------------------------------------------
# Schema builders — LDA and NMF output → detected_trends documents
# ---------------------------------------------------------------------------

def _build_trend_docs_lda(
    df: pd.DataFrame, valid_idx: list, lda_result: dict, calculated_at: datetime
) -> list:
    """
    Assign each tokenized document to its dominant LDA topic via
    get_document_topics(), then build one detected_trends document per topic
    using the same field names BERTopic writes.
    """
    model = lda_result["trainer"].model
    corpus = lda_result["corpus"]  # gensim BoW list, aligned with valid_idx

    # Dominant topic and confidence per document
    assignments, probs = [], []
    for bow in corpus:
        dist = model.get_document_topics(bow, minimum_probability=0)
        tid, prob = max(dist, key=lambda x: x[1]) if dist else (0, 0.0)
        assignments.append(tid)
        probs.append(prob)

    df_v = df.loc[valid_idx].copy().reset_index(drop=True)
    df_v["_topic"] = assignments
    df_v["_topic_prob"] = probs
    max_eng = _max_engagement(df_v, df)

    trend_docs = []
    for tid in range(model.num_topics):
        subset = df_v[df_v["_topic"] == tid]
        if subset.empty:
            continue
        top_words = clean_keywords([w for w, _ in model.show_topic(tid, topn=10)])
        name = "{}_{}".format(tid, "_".join(top_words[:3]))
        rep_docs = list(dict.fromkeys(
            r for r in subset.sort_values("_topic_prob", ascending=False).head(3)["text"]
            if r
        ))
        volume = len(subset)
        total_likes = int(subset["like_count"].sum()) if "like_count" in subset.columns else 0
        total_rts = int(subset["retweet_count"].sum()) if "retweet_count" in subset.columns else 0
        trend_docs.append({
            "topic": tid,
            "Name": name,
            "Representation": top_words,
            "label": generate_topic_label(top_words),
            "representative_docs": rep_docs,
            "volume": volume,
            "total_likes": total_likes,
            "total_retweets": total_rts,
            "trend_score": compute_trend_score(volume, total_likes, total_rts, max_eng),
            **_lang_fields(subset),
            **_tweet_period(subset),
            "calculated_at": calculated_at,
            "model": "lda",
        })

    trend_docs.sort(key=lambda x: x["trend_score"], reverse=True)
    return trend_docs


def _build_trend_docs_nmf(
    df: pd.DataFrame, valid_idx: list, nmf_result: dict, calculated_at: datetime
) -> list:
    """
    Assign each tokenized document to its dominant NMF topic via argmax of
    the document-topic activation matrix, then build detected_trends documents.
    """
    trainer = nmf_result["trainer"]
    tokenized_docs = nmf_result["tokenized_docs"]
    dictionary = nmf_result["dictionary"]

    # Rebuild TF-IDF on the same vocab → doc-topic activation matrix
    tfidf_matrix, _ = prepare_nmf_matrix(tokenized_docs, dictionary)
    H = trainer.model.transform(tfidf_matrix)         # shape (n_docs, n_topics)
    assignments = H.argmax(axis=1).tolist()
    probs = H.max(axis=1).tolist()

    df_v = df.loc[valid_idx].copy().reset_index(drop=True)
    df_v["_topic"] = assignments
    df_v["_topic_prob"] = probs
    max_eng = _max_engagement(df_v, df)

    all_topics = trainer.get_topics(num_words=10)
    trend_docs = []
    for tid in range(nmf_result["num_topics"]):
        subset = df_v[df_v["_topic"] == tid]
        if subset.empty:
            continue
        top_words = clean_keywords(all_topics[tid] if tid < len(all_topics) else [])
        name = "{}_{}".format(tid, "_".join(top_words[:3]))
        rep_docs = list(dict.fromkeys(
            r for r in subset.sort_values("_topic_prob", ascending=False).head(3)["text"]
            if r
        ))
        volume = len(subset)
        total_likes = int(subset["like_count"].sum()) if "like_count" in subset.columns else 0
        total_rts = int(subset["retweet_count"].sum()) if "retweet_count" in subset.columns else 0
        trend_docs.append({
            "topic": tid,
            "Name": name,
            "Representation": top_words,
            "label": generate_topic_label(top_words),
            "representative_docs": rep_docs,
            "volume": volume,
            "total_likes": total_likes,
            "total_retweets": total_rts,
            "trend_score": compute_trend_score(volume, total_likes, total_rts, max_eng),
            **_lang_fields(subset),
            **_tweet_period(subset),
            "calculated_at": calculated_at,
            "model": "nmf",
        })

    trend_docs.sort(key=lambda x: x["trend_score"], reverse=True)
    return trend_docs


# ---------------------------------------------------------------------------
# Per-model deployment runners
# ---------------------------------------------------------------------------

async def _run_lda_deployment() -> dict:
    """Full LDA retrain cycle that writes output to detected_trends."""
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "lda"})
    last_ts = state.get("last_trained_tweet_collected_at") if state else None
    corpus_after_timestamp = last_ts  # incremental by default — only new tweets

    if last_ts:
        new_count = await db["raw_tweets"].count_documents({"collected_at": {"$gt": last_ts}})
        if new_count < DEPLOYED_RETRAIN_THRESHOLD:
            has_topics = await db["detected_trends"].count_documents({"model": "lda"})
            if has_topics > 0:
                logger.info("Skipping LDA: only %d new tweets (minimum %d required)", new_count, DEPLOYED_RETRAIN_THRESHOLD)
                return {"status": "skipped", "reason": "insufficient_new_tweets", "new_tweets_count": new_count}
            # has_topics == 0 — first deployment after evaluation, load full corpus once
            corpus_after_timestamp = None

    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT, after_timestamp=corpus_after_timestamp)
    if df.empty:
        return {"status": "skipped", "reason": "empty_corpus"}

    MIN_PER_LANG = 50
    df_en = df[df["lang_api"] == "en"].copy()
    df_so = df[df["lang_api"] == "so"].copy()

    calculated_at = datetime.now(timezone.utc)
    trend_docs = []
    lda_result_en = lda_result_so = None

    if len(df_en) >= MIN_PER_LANG:
        tokenized_en, valid_idx_en = _tokenize_with_indices(df_en)
        if len(tokenized_en) >= MIN_PER_LANG:
            lda_result_en = await asyncio.to_thread(_run_lda_sync, tokenized_en, RUN_GRID_SEARCH)
            td_en = _build_trend_docs_lda(df, valid_idx_en, lda_result_en, calculated_at)
            for doc in td_en:
                doc["lang"] = "en"
            trend_docs.extend(td_en)
        else:
            logger.warning("LDA-EN: only %d tokenized docs after preprocessing — skipping", len(tokenized_en))
    else:
        logger.warning("LDA-EN: only %d docs (minimum %d) — skipping", len(df_en), MIN_PER_LANG)

    if len(df_so) >= MIN_PER_LANG:
        tokenized_so, valid_idx_so = _tokenize_with_indices(df_so)
        if len(tokenized_so) >= MIN_PER_LANG:
            lda_result_so = await asyncio.to_thread(_run_lda_sync, tokenized_so, RUN_GRID_SEARCH)
            td_so = _build_trend_docs_lda(df, valid_idx_so, lda_result_so, calculated_at)
            for doc in td_so:
                doc["lang"] = "so"
            trend_docs.extend(td_so)
        else:
            logger.warning("LDA-SO: only %d tokenized docs after preprocessing — skipping", len(tokenized_so))
    else:
        logger.warning("LDA-SO: only %d docs (minimum %d) — skipping", len(df_so), MIN_PER_LANG)

    if not trend_docs:
        return {"status": "skipped", "reason": "insufficient_per_language_corpus",
                "en_docs": len(df_en), "so_docs": len(df_so)}

    n_written = await _persist_trend_docs(trend_docs, calculated_at, "lda")
    await _update_last_trained_timestamp("lda", df)

    lda_topics, K_lda = [], 0
    if lda_result_en:
        lda_topics += get_lda_topics(lda_result_en["trainer"].model)
        K_lda += lda_result_en["num_topics"]
    if lda_result_so:
        lda_topics += get_lda_topics(lda_result_so["trainer"].model)
        K_lda += lda_result_so["num_topics"]

    eval_rows = await asyncio.to_thread(_compute_eval_rows_sync, df, "lda", lda_topics, K_lda)
    m = _extract_metrics_from_rows(eval_rows)
    await _write_pipeline_history(
        db=await get_database(),
        model_name="lda",
        calculated_at=calculated_at,
        corpus_size=len(df),
        num_topics=K_lda,
        topics_written=n_written,
        **m,
    )

    return {
        "status": "success",
        "model": "lda",
        "topics_written": n_written,
        "num_topics": K_lda,
        "calculated_at": calculated_at.isoformat(),
    }


async def _run_nmf_deployment() -> dict:
    """Full NMF retrain cycle that writes output to detected_trends."""
    db = await get_database()
    state = await db["pipeline_state"].find_one({"pipeline": "nmf"})
    last_ts = state.get("last_trained_tweet_collected_at") if state else None
    corpus_after_timestamp = last_ts  # incremental by default — only new tweets

    if last_ts:
        new_count = await db["raw_tweets"].count_documents({"collected_at": {"$gt": last_ts}})
        if new_count < DEPLOYED_RETRAIN_THRESHOLD:
            has_topics = await db["detected_trends"].count_documents({"model": "nmf"})
            if has_topics > 0:
                logger.info("Skipping NMF: only %d new tweets (minimum %d required)", new_count, DEPLOYED_RETRAIN_THRESHOLD)
                return {"status": "skipped", "reason": "insufficient_new_tweets", "new_tweets_count": new_count}
            # has_topics == 0 — first deployment after evaluation, load full corpus once
            corpus_after_timestamp = None

    count = await get_corpus_count()
    if count < MIN_CORPUS_SIZE:
        return {"status": "skipped", "reason": "insufficient_corpus", "corpus_count": count}

    df = await load_tweet_corpus(lang=None, limit=CORPUS_LIMIT, after_timestamp=corpus_after_timestamp)
    if df.empty:
        return {"status": "skipped", "reason": "empty_corpus"}

    MIN_PER_LANG = 50
    df_en = df[df["lang_api"] == "en"].copy()
    df_so = df[df["lang_api"] == "so"].copy()

    calculated_at = datetime.now(timezone.utc)
    trend_docs = []
    nmf_result_en = nmf_result_so = None

    if len(df_en) >= MIN_PER_LANG:
        tokenized_en, valid_idx_en = _tokenize_with_indices(df_en)
        if len(tokenized_en) >= MIN_PER_LANG:
            nmf_result_en = await asyncio.to_thread(_run_nmf_sync, tokenized_en, RUN_GRID_SEARCH)
            td_en = _build_trend_docs_nmf(df, valid_idx_en, nmf_result_en, calculated_at)
            for doc in td_en:
                doc["lang"] = "en"
            trend_docs.extend(td_en)
        else:
            logger.warning("NMF-EN: only %d tokenized docs after preprocessing — skipping", len(tokenized_en))
    else:
        logger.warning("NMF-EN: only %d docs (minimum %d) — skipping", len(df_en), MIN_PER_LANG)

    if len(df_so) >= MIN_PER_LANG:
        tokenized_so, valid_idx_so = _tokenize_with_indices(df_so)
        if len(tokenized_so) >= MIN_PER_LANG:
            nmf_result_so = await asyncio.to_thread(_run_nmf_sync, tokenized_so, RUN_GRID_SEARCH)
            td_so = _build_trend_docs_nmf(df, valid_idx_so, nmf_result_so, calculated_at)
            for doc in td_so:
                doc["lang"] = "so"
            trend_docs.extend(td_so)
        else:
            logger.warning("NMF-SO: only %d tokenized docs after preprocessing — skipping", len(tokenized_so))
    else:
        logger.warning("NMF-SO: only %d docs (minimum %d) — skipping", len(df_so), MIN_PER_LANG)

    if not trend_docs:
        return {"status": "skipped", "reason": "insufficient_per_language_corpus",
                "en_docs": len(df_en), "so_docs": len(df_so)}

    n_written = await _persist_trend_docs(trend_docs, calculated_at, "nmf")
    await _update_last_trained_timestamp("nmf", df)

    nmf_topics, K_nmf = [], 0
    if nmf_result_en:
        nmf_topics += get_nmf_topics(nmf_result_en["trainer"])
        K_nmf += nmf_result_en["num_topics"]
    if nmf_result_so:
        nmf_topics += get_nmf_topics(nmf_result_so["trainer"])
        K_nmf += nmf_result_so["num_topics"]

    eval_rows = await asyncio.to_thread(_compute_eval_rows_sync, df, "nmf", nmf_topics, K_nmf)
    m = _extract_metrics_from_rows(eval_rows)
    await _write_pipeline_history(
        db=await get_database(),
        model_name="nmf",
        calculated_at=calculated_at,
        corpus_size=len(df),
        num_topics=K_nmf,
        topics_written=n_written,
        **m,
    )

    return {
        "status": "success",
        "model": "nmf",
        "topics_written": n_written,
        "num_topics": K_nmf,
        "calculated_at": calculated_at.isoformat(),
    }
